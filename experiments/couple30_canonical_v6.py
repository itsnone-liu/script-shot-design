# -*- coding: utf-8 -*-
"""C2 转正组 v6 —— 2026-09-16 晚（正面真实照到手，胖瘦数值实锤）。

实测：真实正面照 h/w = 1.384/1.393/1.437（≈1.40 窄长脸）；全部生成版 1.09-1.15
——Klein 生成板的脸型先验压在 1.1，形容词推不动，ReActor 内脸救不了外轮廓。
v6 换根：
  front/talk = 真实正面照当载体（ref10 脸最大最清楚；化妆无妨，ReActor 用 ref03
               重写内脸身份），Klein 只做 变清晰+标准照化/说话口型，几何零发明；
  up/down     = 数值化脸型指令板（"脸长约为宽度 1.4 倍"），拒绝形容词；
  全部输出过 h/w 闸门（目标 1.30-1.55）+ cos。

产物：canonical_v6/{front,up,down,talk}.png + canonical_v6_report.json + _v6_compare.jpg
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
CARRIER = EXTRA / "ref10.jpg"     # 脸最大最清楚（化妆无妨，内脸会被重写）
IDENTITY = EXTRA / "ref03.jpg"    # 身份锚（中心 avg 0.692）
KLEIN_WEBAPP = "2075052610570244098"

SHAPE_LOCK = ("严格保持她的脸型与五官几何完全不变：脸是窄长的鹅蛋脸，脸的长度约为宽度的 1.4 倍，"
              "脸颊平坦、下颌线窄而清晰——脸部长宽比一个像素都不许变宽，不变圆，不显胖。")
DEBLUR = ("把这张有些模糊的照片变成清晰的摄影棚标准照：完全相同的脸型、五官、发型、"
          "头部角度与头肩构图，只提高清晰度、皮肤质感与灯光（柔和均匀，浅灰背景），"
          "表情保持原样自然。" )
POSES = {
    "front": CARRIER,   # 载体路线：真实照 → 变清晰
    "talk": CARRIER,    # 载体路线：真实照 → 变清晰 + 说话口型
    "up": None,         # 板路线：数值脸型指令
    "down": None,
}
TALK_EXTRA = ("然后让她张开嘴唇呈正在说话的口型，眼神生动看向镜头方向，"
              "脸上有自然笑意。除此之外一切保持不变。")
NUMERIC_PLATE = ("图一与图二是同一位真实女性。她有一张窄长的鹅蛋脸：脸的长度约为宽度的 1.4 倍，"
                 "脸颊平坦内收、没有婴儿肥，下颌线窄而清晰，颧骨不外扩，面部脂肪感低。"
                 "严格保持她的五官、发型（深棕色及肩中长直发）、肤色与气质——是同一个人。")
POSE_INSTR = {
    "up": "低角度仰拍：镜头从下方约 30 度仰角拍摄，她微微仰起脸，下巴微抬，"
          "双眼看向镜头，脸上带轻松笑意。保持窄长脸型不因仰角变宽。",
    "down": "高角度俯拍：镜头从上方约 30 度俯角拍摄，她头部自然放平略低，"
            "双眼看镜头，低头浅笑。保持窄长脸型，俯角不改变脸部长宽比。",
}
STYLE = ("摄影棚标准照构图，头肩像，高清写实人像摄影，表情生动自然，眼神明亮有神。")
RATIO_LO, RATIO_HI = 1.28, 1.58


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
        {"nodeId": "500", "fieldName": "text", "fieldValue": instr},
    ]
    tid = rh_task.run_webapp(key, KLEIN_WEBAPP, node_info)
    print(f"[klein] task {tid} -> {dest.name}", flush=True)
    out = rh_task.wait_task(key, tid, poll=8, max_wait=900,
                            on_progress=lambda t, s: print(f"  {s}", flush=True))
    for url in rh_task.collect_file_urls(out):
        if url.lower().split("?")[0].endswith((".png", ".jpg", ".jpeg", ".webp")):
            rh_task.download(url, dest)
            print(f"[klein] saved {dest.name}"); return dest
    raise SystemExit(f"klein failed: {dest.name}")


_FC = FaceComparator()
_E03 = _FC.embed(_FC.largest_face(cv2.imread(str(IDENTITY))))


def face_probe(path: Path) -> tuple[float | None, float | None, int]:
    img = cv2.imread(str(path))
    if img is None:
        return None, None, 0
    h, w = img.shape[:2]
    _FC.det.setInputSize((w, h))
    _, faces = _FC.det.detect(img)
    if faces is None or len(faces) == 0:
        return None, None, 0
    areas = faces[:, 2] * faces[:, 3]
    f = faces[int(np.argmax(areas))]
    ratio = float(f[3] / f[2])
    face = _FC.rec.alignCrop(img, f)
    cos = float(_FC.cosine(_FC.embed(face), _E03))
    return ratio, cos, int(len(faces))


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
    DST = IDENT / "canonical_v6"
    DST.mkdir(parents=True, exist_ok=True)
    api = json.loads((P820 / "data" / "api_format" / "_reactor_single_c30.json").read_text(encoding="utf-8"))
    sf.WORKFLOWS["reactor_c30"] = {
        "workflow_id": "_reactor_single_c30", "webapp_id": "",
        "ref": "2.image", "target": "1.image", "note": "C2 v3+: restore 0.25"}

    rows = []
    for name in ("front", "talk", "up", "down"):
        if POSES[name] is not None:  # 载体路线
            instr = SHAPE_LOCK + DEBLUR + (TALK_EXTRA if name == "talk" else "")
            plate = klein(instr, POSES[name], DST / f"{name}_carrier.png")
        else:  # 数值板路线
            plate = klein(NUMERIC_PLATE + POSE_INSTR[name] + SHAPE_LOCK + STYLE,
                          IDENTITY, DST / f"{name}_plate.png")
        out = reactor(plate, f"c30v6_{name}")
        dest = DST / f"{name}.png"
        shutil.copy(out, dest)
        ratio, cos, nf = face_probe(dest)
        ok = ratio is not None and RATIO_LO <= ratio <= RATIO_HI and nf == 1
        rows.append({"name": name, "h_over_w": ratio, "cos_vs_ref03": round(cos, 4) if cos else None,
                     "n_faces": nf, "ratio_gate": f"{RATIO_LO}-{RATIO_HI}",
                     "verdict": "PASS" if ok else "CHECK"})
        print(f"[v6:{name}] h/w={ratio} cos={cos} faces={nf} -> {'PASS' if ok else 'CHECK'}", flush=True)

    (DST / "canonical_v6_report.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    tiles = [("REF08 real", EXTRA / "ref08.jpg"), ("REF10 real", EXTRA / "ref10.jpg"),
             ("V5 front(旧)", IDENT / "canonical_v5/front.png"), ("V6 front", DST / "front.png"),
             ("V5 talk(旧)", IDENT / "canonical_v5/talk.png"), ("V6 talk", DST / "talk.png"),
             ("V6 up", DST / "up.png"), ("V6 down", DST / "down.png")]
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
    cv2.imwrite(str(DST / "_v6_compare.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(f"sheet -> {DST / '_v6_compare.jpg'}")


if __name__ == "__main__":
    main()
