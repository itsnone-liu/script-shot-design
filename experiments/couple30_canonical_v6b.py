# -*- coding: utf-8 -*-
"""C2 转正组 v6b —— 2026-09-16 深夜（v6 修补）。

v6 发现：talk 从糊图直接改口型 → Klein 大改下半脸丢形(1.437→1.124)；
背景混入小人脸；down 撞平台 805。
v6b：talk/up 都从已成型的 front_carrier.png（形状已对）做小步编辑；
down 重跑数值板；所有输出主脸方形裁切（根除背景脸+统一锚规格）。
"""
from __future__ import annotations

import io
import json
import shutil
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

ROOT = Path(__file__).resolve().parents[1]
P820 = Path(__file__).resolve().parents[2] / "820"
sys.path.insert(0, str(P820))
sys.path.insert(0, str(P820 / "experiments"))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import swap_face as sf  # noqa: E402
from experiments import rh_task  # noqa: E402
from experiments.metrics import FaceComparator  # noqa: E402

IDENT = ROOT / "examples" / "couple30_v1" / "identity"
EXTRA = IDENT / "refs_extra"
V6 = IDENT / "canonical_v6"
CARRIER = V6 / "front_carrier.png"   # 形状已对的去模糊载体
IDENTITY = EXTRA / "ref03.jpg"
KLEIN_WEBAPP = "2075052610570244098"
RATIO_LO, RATIO_HI = 1.28, 1.58

SHAPE_LOCK = ("严格保持她的脸型与五官几何完全不变：脸是窄长的鹅蛋脸，脸的长度约为宽度的 1.4 倍，"
              "脸颊平坦、下颌线窄而清晰——脸部长宽比不变宽、不变圆、不显胖。")
EDITS = {
    "talk": ("只做一个修改：让她张开嘴唇呈正在说话的口型，眼神看向镜头方向，脸上有自然笑意。"
             "脸型、发型、构图、灯光、背景全部保持不变。"),
    "up": ("只改变镜头角度：镜头移到下方约 30 度仰角拍摄，她微微仰起脸，下巴微抬，"
           "双眼看向镜头，脸上带轻松笑意。人物、发型、灯光风格保持不变，脸型保持窄长不变宽。"),
    "down": ("只改变镜头角度：镜头移到上方约 30 度俯角拍摄，她头部自然放平略低，"
             "双眼看镜头，低头浅笑。人物、发型、灯光风格保持不变，脸型保持窄长，"
             "俯角不改变脸部长宽比。"),
}


def klein(instr: str, carrier: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"[klein] cached {dest.name}"); return dest
    key = rh_task.load_api_key()
    u1 = rh_task.upload_file(key, carrier)
    u2 = rh_task.upload_file(key, IDENTITY)
    node_info = [
        {"nodeId": "597", "fieldName": "image", "fieldValue": u1},
        {"nodeId": "598", "fieldName": "image", "fieldValue": u2},
        {"nodeId": "500", "fieldName": "text", "fieldValue": SHAPE_LOCK + instr},
    ]
    tid = rh_task.run_webapp(key, KLEIN_WEBAPP, node_info)
    print(f"[klein] task {tid} -> {dest.name}", flush=True)
    for attempt in range(3):
        try:
            out = rh_task.wait_task(key, tid, poll=8, max_wait=900,
                                    on_progress=lambda t, s: print(f"  {s}", flush=True))
            break
        except Exception as e:  # noqa: BLE001
            print(f"[klein] wait retry {attempt}: {e}")
            if attempt == 2:
                raise
    for url in rh_task.collect_file_urls(out):
        if url.lower().split("?")[0].endswith((".png", ".jpg", ".jpeg", ".webp")):
            rh_task.download(url, dest)
            print(f"[klein] saved {dest.name}"); return dest
    raise SystemExit(f"klein failed: {dest.name}")


_FC = FaceComparator()
_E03 = _FC.embed(_FC.largest_face(cv2.imread(str(IDENTITY))))


def crop_main_face(path: Path, dest: Path) -> Path:
    """主脸方形裁切（2.4x2.6 余量），根除背景脸。"""
    img = cv2.imread(str(path))
    h, w = img.shape[:2]
    _FC.det.setInputSize((w, h))
    _, faces = _FC.det.detect(img)
    areas = faces[:, 2] * faces[:, 3]
    f = faces[int(np.argmax(areas))]
    x, y, fw, fh = (float(v) for v in f[:4])
    side = max(fw * 2.4, fh * 2.6)
    cx, cy = x + fw / 2, y + fh / 2 + fh * 0.15
    x0 = max(0, min(int(cx - side / 2), w - int(side)))
    y0 = max(0, min(int(cy - side / 2), h - int(side)))
    crop = img[y0:y0 + int(side), x0:x0 + int(side)]
    cv2.imwrite(str(dest), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return dest


def probe(path: Path) -> tuple[float | None, float | None, int]:
    img = cv2.imread(str(path))
    h, w = img.shape[:2]
    _FC.det.setInputSize((w, h))
    _, faces = _FC.det.detect(img)
    if faces is None or len(faces) == 0:
        return None, None, 0
    areas = faces[:, 2] * faces[:, 3]
    f = faces[int(np.argmax(areas))]
    face = _FC.rec.alignCrop(img, f)
    return float(f[3] / f[2]), float(_FC.cosine(_FC.embed(face), _E03)), int(len(faces))


def reactor(plate: Path, tag: str) -> Path:
    meta = sf.run_swap("reactor_c30", plate, IDENTITY, tag=tag, max_wait=600)
    best, best_cos = None, -1.0
    for f in [Path(x) for x in meta.get("files", [])]:
        face = _FC.largest_face(cv2.imread(str(f)))
        if face is None:
            continue
        cos = float(_FC.cosine(_FC.embed(face), _E03))
        if cos > best_cos:
            best, best_cos = f, cos
    if best is None:
        raise RuntimeError(f"reactor no-face: {tag}")
    return best


def main() -> None:
    V6.mkdir(parents=True, exist_ok=True)
    api = json.loads((P820 / "data" / "api_format" / "_reactor_single_c30.json").read_text(encoding="utf-8"))
    sf.WORKFLOWS["reactor_c30"] = {
        "workflow_id": "_reactor_single_c30", "webapp_id": "",
        "ref": "2.image", "target": "1.image", "note": "C2 v3+: restore 0.25"}

    rows = []
    for name in ("talk", "up", "down"):
        edit = klein(EDITS[name], CARRIER, V6 / f"{name}_carrier2.png")
        out = reactor(edit, f"c30v6b_{name}")
        raw = V6 / f"{name}_raw.png"
        shutil.copy(out, raw)
        dest = crop_main_face(raw, V6 / f"{name}.png")
        ratio, cos, nf = probe(dest)
        ok = ratio is not None and RATIO_LO <= ratio <= RATIO_HI and nf == 1
        rows.append({"name": name, "h_over_w": round(ratio, 3) if ratio else None,
                     "cos_vs_ref03": round(cos, 4) if cos else None,
                     "n_faces": nf, "verdict": "PASS" if ok else "CHECK"})
        print(f"[v6b:{name}] h/w={ratio} cos={cos} faces={nf} -> {'PASS' if ok else 'CHECK'}", flush=True)
    raw = V6 / "front_raw.png"
    if not raw.exists():
        shutil.copy(V6 / "front.png", raw)
    crop_main_face(raw, V6 / "front.png")  # 统一裁切（顺带清掉潜在边角脸）
    ratio, cos, nf = probe(V6 / "front.png")
    rows.insert(0, {"name": "front", "h_over_w": round(ratio, 3) if ratio else None,
                    "cos_vs_ref03": round(cos, 4) if cos else None, "n_faces": nf,
                    "verdict": "PASS" if (ratio and RATIO_LO <= ratio <= RATIO_HI and nf == 1) else "CHECK"})
    print(f"[v6b:front] h/w={ratio} cos={cos} faces={nf}", flush=True)
    (V6 / "canonical_v6_report.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    tiles = [("REF08", EXTRA / "ref08.jpg"), ("REF10", EXTRA / "ref10.jpg"),
             ("V5 front", IDENT / "canonical_v5/front.png"), ("V6 front", V6 / "front.png"),
             ("V5 talk", IDENT / "canonical_v5/talk.png"), ("V6 talk", V6 / "talk.png"),
             ("V6 up", V6 / "up.png"), ("V6 down", V6 / "down.png")]
    cell = 300
    sheet = np.full((2 * cell + 60, 4 * cell, 3), 245, np.uint8)
    for i, (label, path) in enumerate(tiles):
        r, c = divmod(i, 4)
        x0, y0 = c * cell + 8, r * cell + 40
        img = cv2.imread(str(path)) if path.exists() else None
        if img is None:
            cv2.putText(sheet, "MISSING", (x0 + 80, y0 + 140), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80, 80, 80), 2)
        else:
            h, w = img.shape[:2]
            s = (cell - 16) / max(h, w)
            img = cv2.resize(img, (int(w * s), int(h * s)))
            hh, ww = img.shape[:2]
            sheet[y0:y0 + hh, x0:x0 + ww] = img
        cv2.putText(sheet, label, (c * cell + 8, r * cell + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (30, 30, 180), 2)
    cv2.imwrite(str(V6 / "_v6_compare.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(f"sheet -> {V6 / '_v6_compare.jpg'}")


if __name__ == "__main__":
    main()
