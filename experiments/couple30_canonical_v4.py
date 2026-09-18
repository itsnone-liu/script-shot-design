# -*- coding: utf-8 -*-
"""C2 转正组 v4 —— 2026-09-16（v3 用户反馈：生成脸太圆显胖）。

诊断：v2 板偏长（Klein 默认漂移）→ v3 提示词写"圆润鹅蛋/脸颊饱满"矫枉过正。
两次都是形容词泄漏——ReActor 只写内脸，下颌外轮廓永远跟板。
v4：零脸型形容词 + 反漂移子句，脸型唯一来源=ref03 真实几何。

产物：canonical_v4/{front,up,down,talk}.png + 三版正面并排 _front_compare.jpg
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
PLATES = IDENT / "canonical_v4_plates"
DST = IDENT / "canonical_v4"
REF = IDENT / "refs_extra" / "ref03.jpg"
KLEIN_WEBAPP = "2075052610570244098"

BASE = ("图一与图二是同一位真实女性。严格保持她的五官、脸型、发型（深棕色及肩中长直发）、"
        "肤色与气质完全一致——是同一个人，不是相似的人。"
        "她的脸型以图二参考照的真实脸型为准，严格原样保持：不拉长、不缩短、"
        "不圆润化、不显胖、不显瘦、不美化，脸颊饱满度也严格照原样。")
STYLE = ("摄影棚标准照构图，头肩像，柔和均匀灯光，浅灰背景，高清写实人像摄影，"
         "表情生动自然，眼神明亮有神。")
POSES = {
    "front": "把她的头部转向正对镜头：面部完全朝前，双眼平视镜头，"
             "带着含真实暖意的微笑，嘴角自然上扬，眼睛微弯有笑意。",
    "up": "低角度仰拍：镜头从下方约 30 度仰角拍摄，她微微仰起脸，下巴微抬，"
          "双眼看向镜头，脸上带轻松笑意。",
    "down": "高角度俯拍：镜头从上方约 30 度俯角拍摄，她头部自然放平略低，"
            "双眼看镜头，低头浅笑。",
    "talk": "说话标准照：头部正对镜头，嘴唇微微张开呈正在说话的口型，"
            "像对着面前的人轻声说心里话，眼神生动看向镜头略偏下方，脸上有笑意。",
}


def gen_plate(name: str) -> Path:
    PLATES.mkdir(parents=True, exist_ok=True)
    dest = PLATES / f"{name}.png"
    if dest.exists():
        print(f"[plate:{name}] cached"); return dest
    key = rh_task.load_api_key()
    u = rh_task.upload_file(key, REF)
    node_info = [
        {"nodeId": "597", "fieldName": "image", "fieldValue": u},
        {"nodeId": "598", "fieldName": "image", "fieldValue": u},
        {"nodeId": "500", "fieldName": "text", "fieldValue": BASE + POSES[name] + STYLE},
    ]
    tid = rh_task.run_webapp(key, KLEIN_WEBAPP, node_info)
    print(f"[plate:{name}] task {tid}", flush=True)
    out = rh_task.wait_task(key, tid, poll=8, max_wait=900,
                            on_progress=lambda t, s: print(f"[plate:{name}] {s}", flush=True))
    for url in rh_task.collect_file_urls(out):
        if url.lower().split("?")[0].endswith((".png", ".jpg", ".jpeg", ".webp")):
            rh_task.download(url, dest)
            print(f"[plate:{name}] saved"); return dest
    raise SystemExit(f"plate {name}: no image output")


def face_ratio(img_path: Path) -> float | None:
    """YuNet 脸框高宽比（观感胖瘦的粗代理）。"""
    fc = _FC
    img = cv2.imread(str(img_path))
    if img is None:
        return None
    h, w = img.shape[:2]
    fc.det.setInputSize((w, h))
    _, faces = fc.det.detect(img)
    if faces is None or len(faces) == 0:
        return None
    areas = faces[:, 2] * faces[:, 3]
    f = faces[int(np.argmax(areas))]
    return round(float(f[3] / f[2]), 3)  # h/w


_FC = FaceComparator()
_E_CENTER = _FC.embed(_FC.largest_face(cv2.imread(str(REF))))


def main() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    api = json.loads((P820 / "data" / "api_format" / "_reactor_single_c30.json").read_text(encoding="utf-8"))
    sf.WORKFLOWS["reactor_c30"] = {
        "workflow_id": "_reactor_single_c30", "webapp_id": "",
        "ref": "2.image", "target": "1.image", "note": "C2 v3/v4: restore 0.25"}

    rows = []
    for name in POSES:
        plate = gen_plate(name)
        meta = sf.run_swap("reactor_c30", plate, REF, tag=f"c30v4_{name}", max_wait=600)
        files = [Path(f) for f in meta.get("files", [])]
        pngs = [f for f in files if f.suffix.lower() == ".png"] or files
        best, best_cos = None, -1.0
        for f in pngs:
            face = _FC.largest_face(cv2.imread(str(f)))
            if face is None:
                continue
            cos = float(_FC.cosine(_FC.embed(face), _E_CENTER))
            if cos > best_cos:
                best, best_cos = f, cos
        if best is None:
            rows.append({"name": name, "verdict": "FAIL"}); continue
        dest = DST / f"{name}.png"
        shutil.copy(best, dest)
        rows.append({"name": name, "file": str(dest), "cos_center": round(best_cos, 4),
                     "face_ratio": face_ratio(dest), "verdict": "PASS" if best_cos >= 0.55 else "LOW"})
        print(f"[{name}] cos={best_cos:.4f} ratio={rows[-1]['face_ratio']}", flush=True)

    (DST / "canonical_v4_report.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    # 三版正面并排（校准用） + 参考脸型比
    print("\n=== face h/w ratio guardrail ===")
    for tag, p in [("ref01(3/4真实)", IDENT / "ref_original.jpg"),
                   ("ref03(3/4真实)", REF),
                   ("v2 front", IDENT / "canonical_v2" / "front.png"),
                   ("v3 front", IDENT / "canonical_v3" / "front.png"),
                   ("v4 front", DST / "front.png")]:
        print(f"{tag:16} {face_ratio(p)}")

    tiles = [("REF03", REF), ("V2 front(长)", IDENT / "canonical_v2" / "front.png"),
             ("V3 front(圆)", IDENT / "canonical_v3" / "front.png"), ("V4 front", DST / "front.png"),
             ("V4 up", DST / "up.png"), ("V4 down", DST / "down.png"), ("V4 talk", DST / "talk.png")]
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
        cv2.putText(sheet, label, (c * cell + 8, r * cell + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 30, 180), 2)
    cv2.imwrite(str(DST / "_front_compare.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(f"\nsheet -> {DST / '_front_compare.jpg'}")


if __name__ == "__main__":
    main()
