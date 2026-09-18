# -*- coding: utf-8 -*-
"""C2 转正组 v5 —— 2026-09-16（用户："3456 还是偏胖"）。

背景：用户以侧脸照为胖瘦基准（侧脸显窄是几何事实），正脸双侧脸颊全露必然显宽；
VLM 的"+0.5 适中"与用户感知错位 → 以用户为准，向瘦校准。
策略：一档瘦（全部 4 角度）+ 两档瘦（仅 front 作校准极端），一轮夹逼出用户要的档位。

产物：canonical_v5/{front,up,down,talk}.png + canonical_v5/front_2notch.png + _v5_compare.jpg
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
REF = IDENT / "refs_extra" / "ref03.jpg"
KLEIN_WEBAPP = "2075052610570244098"

BASE_V5 = ("图一与图二是同一位真实女性。严格保持她的五官、发型（深棕色及肩中长直发）、"
           "肤色与气质——是同一个人，不是相似的人。她的脸型以图二参考照为准并略微清瘦："
           "脸颊自然内收不鼓胀，下颌线清晰收拢，脸宽比参考照的侧面观感更窄一点，"
           "绝不显胖、不圆润化、不婴儿肥，也不拉长变形。")
SLIM_2NOTCH = ("图一与图二是同一位真实女性。严格保持她的五官、发型、肤色与气质。"
               "她的脸型清瘦：脸颊明显内收，颧骨线条清晰，下颌线锐利收窄呈窄鹅蛋脸，"
               "面部脂肪感低，完全不胖。")
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


def klein_plate(instr: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"[plate] cached {dest.name}"); return dest
    key = rh_task.load_api_key()
    u = rh_task.upload_file(key, REF)
    node_info = [
        {"nodeId": "597", "fieldName": "image", "fieldValue": u},
        {"nodeId": "598", "fieldName": "image", "fieldValue": u},
        {"nodeId": "500", "fieldName": "text", "fieldValue": instr},
    ]
    tid = rh_task.run_webapp(key, KLEIN_WEBAPP, node_info)
    print(f"[plate] task {tid} -> {dest.name}", flush=True)
    out = rh_task.wait_task(key, tid, poll=8, max_wait=900,
                            on_progress=lambda t, s: print(f"  {s}", flush=True))
    for url in rh_task.collect_file_urls(out):
        if url.lower().split("?")[0].endswith((".png", ".jpg", ".jpeg", ".webp")):
            rh_task.download(url, dest)
            print(f"[plate] saved {dest.name}"); return dest
    raise SystemExit(f"plate failed: {dest.name}")


_FC = FaceComparator()
_E_CENTER = _FC.embed(_FC.largest_face(cv2.imread(str(REF))))


def reactor_best(plate: Path, tag: str) -> tuple[Path, float]:
    meta = sf.run_swap("reactor_c30", plate, REF, tag=tag, max_wait=600)
    best, best_cos = None, -1.0
    for f in [Path(x) for x in meta.get("files", [])]:
        face = _FC.largest_face(cv2.imread(str(f)))
        if face is None:
            continue
        cos = float(_FC.cosine(_FC.embed(face), _E_CENTER))
        if cos > best_cos:
            best, best_cos = f, cos
    if best is None:
        raise RuntimeError(f"reactor no-face: {tag}")
    return best, best_cos


def main() -> None:
    DST = IDENT / "canonical_v5"
    PLATES = IDENT / "canonical_v5_plates"
    DST.mkdir(parents=True, exist_ok=True)
    api = json.loads((P820 / "data" / "api_format" / "_reactor_single_c30.json").read_text(encoding="utf-8"))
    sf.WORKFLOWS["reactor_c30"] = {
        "workflow_id": "_reactor_single_c30", "webapp_id": "",
        "ref": "2.image", "target": "1.image", "note": "C2 v3+: restore 0.25"}

    rows = []
    for name in POSES:
        plate = klein_plate(BASE_V5 + POSES[name] + STYLE, PLATES / f"{name}.png")
        out, cos = reactor_best(plate, f"c30v5_{name}")
        dest = DST / f"{name}.png"
        shutil.copy(out, dest)
        rows.append({"name": name, "cos_center": round(cos, 4),
                     "verdict": "PASS" if cos >= 0.55 else "LOW"})
        print(f"[v5:{name}] cos={cos:.4f}", flush=True)
    # 两档瘦校准极端（仅 front）
    plate2 = klein_plate(SLIM_2NOTCH + POSES["front"] + STYLE, PLATES / "front_2notch.png")
    out2, cos2 = reactor_best(plate2, "c30v5_front2n")
    shutil.copy(out2, DST / "front_2notch.png")
    rows.append({"name": "front_2notch", "cos_center": round(cos2, 4)})
    print(f"[v5:front_2notch] cos={cos2:.4f}", flush=True)
    (DST / "canonical_v5_report.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    tiles = [("REF03", REF),
             ("V4 front", IDENT / "canonical_v4" / "front.png"),
             ("V5 front 瘦1档", DST / "front.png"),
             ("V5b front 瘦2档", DST / "front_2notch.png"),
             ("V4 down", IDENT / "canonical_v4" / "down.png"),
             ("V5 down", DST / "down.png"),
             ("V5 up", DST / "up.png"),
             ("V5 talk", DST / "talk.png")]
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
    cv2.imwrite(str(DST / "_v5_compare.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(f"sheet -> {DST / '_v5_compare.jpg'}")


if __name__ == "__main__":
    main()
