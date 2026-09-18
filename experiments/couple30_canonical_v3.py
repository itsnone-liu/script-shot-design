# -*- coding: utf-8 -*-
"""C2 身份资产包 · L1 转正组 v3 —— 2026-09-16（用户反馈驱动重做）。

用户对 v2 的三条意见 → v3 对策：
  脸显稍长   → 姿态板提示词显式压圆润鹅蛋脸/短软下颌/脸颊饱满（板下巴漏出是主因）
  眼睛不对称 → restore 0.4→0.25；左脸参考补位（ref02-07 全左3/4，远眼不再靠发明）
  表情不生动 → 板表情烘生动（暖意微笑/眼神明亮/说话口型）

结构升级：左/右 3/4 用真实照片（真实 > 重画，concert30 定律），只生成
front/up/down/talk 四个缺失角度；每角度 Klein 新板 × 双参考 ReActor 竞标。

产物：identity/canonical_v3/{front,up,down,talk}.png + left34.jpg/right34.jpg(真实裁切)
     + canonical_v3_report.json + _sheet.jpg
"""
from __future__ import annotations

import io
import json
import shutil
import sys
import time
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
PLATES = IDENT / "canonical_v3_plates"
DST = IDENT / "canonical_v3"
REF = {  # 本地参考图（ref03=身份中心锚 avg0.692）
    "ref01": IDENT / "ref_original.jpg",
    "ref03": EXTRA / "ref03.jpg",
    "ref06": EXTRA / "ref06.jpg",
    "ref07": EXTRA / "ref07.jpg",
}
KLEIN_WEBAPP = "2075052610570244098"
N_IMG1, N_IMG2, N_TEXT = "597", "598", "500"

BASE = ("图一与图二是同一位真实女性。她脸型是圆润的鹅蛋脸，下颌线柔和较短，脸颊饱满，"
        "严格保持她的五官、发型（深棕色及肩中长直发）、肤色与气质——是同一个人，不是相似的人。")
STYLE = ("摄影棚标准照构图，头肩像，柔和均匀灯光，浅灰背景，高清写实人像摄影，"
         "表情生动自然，眼神明亮有神，不要僵硬的证件照表情。")
PLATE_PROMPTS = {
    "front": "正面标准照：头部正对镜头，面部完全朝前，双眼平视镜头，"
             "带着含真实暖意的微笑，嘴角自然上扬，眼睛微弯有笑意。",
    "up": "低角度仰拍标准照：镜头从下方约 30 度仰角拍摄，她微微仰起脸，"
          "下巴微抬，双眼看向镜头，脸上带轻松的笑意，保留完整下颌与颈部线条，下巴圆润不拉长。",
    "down": "高角度俯拍标准照：镜头从上方约 30 度俯角拍摄，她头部自然放平略低，"
            "双眼看镜头，低头浅笑，眼神温柔朝向镜头。",
    "talk": "说话标准照：头部正对镜头，嘴唇微微张开呈正在说话的口型，"
            "像对着面前的人轻声说心里话，眼神生动看向镜头略偏下方，脸上有笑意。",
}
# 每角度竞标参考（近原生角度优先，ref03 恒定参赛）
BID_REFS = {"front": ["ref03", "ref01"], "up": ["ref03", "ref01"],
            "down": ["ref03", "ref07"], "talk": ["ref03", "ref06"]}
GATE = 0.55


def gen_plate(name: str) -> Path:
    PLATES.mkdir(parents=True, exist_ok=True)
    dest = PLATES / f"{name}.png"
    if dest.exists():
        print(f"[plate:{name}] cached"); return dest
    key = rh_task.load_api_key()
    u = rh_task.upload_file(key, REF["ref03"])
    instr = BASE + PLATE_PROMPTS[name] + STYLE
    node_info = [
        {"nodeId": N_IMG1, "fieldName": "image", "fieldValue": u},
        {"nodeId": N_IMG2, "fieldName": "image", "fieldValue": u},
        {"nodeId": N_TEXT, "fieldName": "text", "fieldValue": instr},
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


def reactor(target: Path, ref_key: str) -> tuple[Path, float]:
    """ReActor 换脸（restore 0.25 自有副本流），返回 (最佳输出, cos_vs_ref03)。"""
    fc = _FC
    e_center = _E_CENTER
    tag = f"c30v3_{target.stem}_{ref_key}"
    meta = sf.run_swap("reactor_c30", target, REF[ref_key], tag=tag, max_wait=600)
    files = [Path(f) for f in meta.get("files", [])]
    pngs = [f for f in files if f.suffix.lower() == ".png"] or files
    best, best_cos = None, -1.0
    for f in pngs:
        face = fc.largest_face(cv2.imread(str(f)))
        if face is None:
            continue
        cos = float(fc.cosine(fc.embed(face), e_center))
        if cos > best_cos:
            best, best_cos = f, cos
    if best is None:
        raise RuntimeError(f"reactor no-face output for {target.stem}<-{ref_key}")
    return best, best_cos


def face_crop_square(src: Path, dest: Path) -> None:
    """真实照片 → 方形脸裁切（P1 同款策略），作原生角度 canonical。"""
    fc = _FC
    img = cv2.imread(str(src))
    h, w = img.shape[:2]
    fc.det.setInputSize((w, h))
    _, faces = fc.det.detect(img)
    areas = faces[:, 2] * faces[:, 3]
    f = faces[int(np.argmax(areas))]
    x, y, fw, fh = (float(v) for v in f[:4])
    side = max(fw * 2.2, fh * 2.4)
    cx, cy = x + fw / 2, y + fh / 2 + fh * 0.18
    x0 = max(0, min(int(cx - side / 2), w - int(side)))
    y0 = max(0, min(int(cy - side / 2), h - int(side)))
    crop = img[y0:y0 + int(side), x0:x0 + int(side)]
    cv2.imwrite(str(dest), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])


_FC = FaceComparator()
_E_CENTER = _FC.embed(_FC.largest_face(cv2.imread(str(REF["ref03"]))))


def main() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    # 注册 restore=0.25 的自有 reactor 流（不动 820 共享 json）
    api = json.loads((P820 / "data" / "api_format" / "_reactor_single.json").read_text(encoding="utf-8"))
    api["15"]["inputs"]["face_restore_visibility"] = 0.25
    (P820 / "data" / "api_format" / "_reactor_single_c30.json").write_text(
        json.dumps(api, ensure_ascii=False), encoding="utf-8")
    sf.WORKFLOWS["reactor_c30"] = {
        "workflow_id": "_reactor_single_c30", "webapp_id": "",
        "ref": "2.image", "target": "1.image",
        "note": "C2 v3: reactor restore 0.25 (eye-symmetry counter-measure)"}

    rows = []
    for name in PLATE_PROMPTS:
        plate = gen_plate(name)
        bids = []
        for rk in BID_REFS[name]:
            try:
                out, cos = reactor(plate, rk)
                bids.append({"ref": rk, "file": str(out), "cos_center": round(cos, 4)})
                print(f"[{name}<-{rk}] cos_vs_ref03={cos:.4f}", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"[{name}<-{rk}] FAILED {e}")
        if not bids:
            rows.append({"name": name, "verdict": "FAIL"}); continue
        win = max(bids, key=lambda b: b["cos_center"])
        dest = DST / f"{name}.png"
        shutil.copy(win["file"], dest)
        rows.append({"name": name, "file": str(dest), "bids": bids,
                     "winner": win["ref"], "cos_center": win["cos_center"],
                     "verdict": "PASS" if win["cos_center"] >= GATE else "LOW"})
        print(f"[{name}] WINNER ref={win['ref']} cos={win['cos_center']}", flush=True)

    # 原生角度：真实照片裁切入组
    face_crop_square(REF["ref03"], DST / "left34.jpg")
    face_crop_square(REF["ref01"], DST / "right34.jpg")
    rows.append({"name": "left34", "file": str(DST / "left34.jpg"), "verdict": "REAL_PHOTO",
                 "source": str(REF["ref03"])})
    rows.append({"name": "right34", "file": str(DST / "right34.jpg"), "verdict": "REAL_PHOTO",
                 "source": str(REF["ref01"])})
    (DST / "canonical_v3_report.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    n_pass = sum(1 for r in rows if r.get("verdict") in ("PASS", "REAL_PHOTO"))
    print(f"--- v3: {n_pass}/{len(rows)} usable")


if __name__ == "__main__":
    main()
