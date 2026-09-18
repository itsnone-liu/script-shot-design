# -*- coding: utf-8 -*-
"""C2 身份资产包 · L1 转正组生成 —— 2026-09-16。

FLUX.2 Klein 指令双图编辑（已验证路线 expert_solutions.flux2_klein_hair validated）
把单张 45° 侧脸原图扩成同人六角度标准照：front / left34 / right34 / up / down / talk。
image1=image2=原图（同图双锚：待编辑载体 + 身份参考），指令驱动转正。

门禁（自动，SFace vs ref_embedding.npy）：front/right34/talk ≥0.50；left34/up/down ≥0.42
（大角度嵌入系统性折扣，concert30 暗场教训）。不过线自动重跑 1 次，再不过标 LOW 留用户裁决。

用法：
    python experiments/couple30_canonical_gen.py            # 全部（串行，约15分钟）
    python experiments/couple30_canonical_gen.py front      # 单角度
    python experiments/couple30_canonical_gen.py --report   # 只重出报告
产物：examples/couple30_v1/identity/canonical/{name}.png + canonical_report.json
"""
from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "820"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from experiments import rh_task  # type: ignore  # noqa: E402
from experiments.metrics import FaceComparator  # noqa: E402

IDENT = ROOT / "examples" / "couple30_v1" / "identity"
CANON = IDENT / "canonical"
KLEIN_WEBAPP = "2075052610570244098"
N_IMG1, N_IMG2, N_TEXT = "597", "598", "500"

IDENTITY = ("图一与图二是同一位真实女性。严格保持她的五官、脸型、发型（深棕色及肩中长直发）、"
            "肤色与气质完全一致——是同一个人，不是相似的人。")
STYLE = ("摄影棚标准照构图，头肩像，柔和均匀灯光，浅灰背景，高清写实人像摄影。")

SHOTS = {
    "front": ("正面标准照：头部正对镜头，面部完全朝前，双眼平视镜头，"
              "表情自然放松带浅微笑，不化妆，不美化。" ),
    "left34": ("左侧 3/4 标准照：头部向她自己的左方转约 45 度，左脸朝向镜头，"
               "视线朝镜头方向，表情自然。"),
    "right34": ("右侧 3/4 标准照：头部向她自己的右方转约 45 度，右脸朝向镜头，"
                "视线朝镜头方向，表情自然（与图二角度相近但更标准）。"),
    "up": ("低角度仰拍标准照：镜头从下方约 30 度仰角拍摄，她微微仰起脸，"
           "下巴微抬，双眼看向镜头，表情自然放松——保留完整的下颌与颈部线条。"),
    "down": ("高角度俯拍标准照：镜头从上方约 30 度俯角拍摄，她头部自然放平，"
             "双眼看镜头，表情自然放松。"),
    "talk": ("说话标准照：头部正对镜头，嘴唇微微张开呈正在说话的口型，"
             "像对着面前的人轻声说话，眼神看向镜头略偏下方，表情生动自然。"),
}
GATE = {"front": 0.50, "right34": 0.50, "talk": 0.50,
        "left34": 0.42, "up": 0.42, "down": 0.42}


def gen_one(fc: FaceComparator, ref_emb, name: str, instr_body: str) -> dict:
    CANON.mkdir(parents=True, exist_ok=True)
    instr = IDENTITY + instr_body + STYLE
    key = rh_task.load_api_key()
    if not key:
        raise SystemExit("missing RunningHub API key")
    rec_path = CANON / f"{name}_state.json"
    for attempt in (1, 2):
        if attempt == 2:
            print(f"[{name}] gate retry (attempt 2)")
        u1 = rh_task.upload_file(key, IDENT / "ref_original.jpg")
        u2 = rh_task.upload_file(key, IDENT / "ref_original.jpg")
        node_info = [
            {"nodeId": N_IMG1, "fieldName": "image", "fieldValue": u1},
            {"nodeId": N_IMG2, "fieldName": "image", "fieldValue": u2},
            {"nodeId": N_TEXT, "fieldName": "text", "fieldValue": instr},
        ]
        t0 = time.time()
        tid = rh_task.run_webapp(key, KLEIN_WEBAPP, node_info)
        print(f"[{name}] task {tid}", flush=True)
        out = rh_task.wait_task(key, tid, poll=8, max_wait=900,
                                on_progress=lambda t, s: print(f"[{name}] {s}", flush=True))
        urls = rh_task.collect_file_urls(out)
        urls = [u for u in urls if u.lower().split("?")[0].endswith((".png", ".jpg", ".jpeg", ".webp"))]
        if not urls:
            print(f"[{name}] no image output, attempt {attempt} failed"); continue
        dest = CANON / f"{name}.png"
        rh_task.download(urls[0], dest)
        # ---- local gate ----
        import cv2  # noqa: E402
        img = cv2.imread(str(dest))
        face = fc.largest_face(img) if img is not None else None
        if face is None:
            print(f"[{name}] no face detected in output"); continue
        cos = float(fc.cosine(fc.embed(face), ref_emb))
        gate = GATE[name]
        ok = cos >= gate
        print(f"[{name}] cos={cos:.4f} gate={gate} {'PASS' if ok else 'LOW'} ({time.time()-t0:.0f}s)")
        rec = {"name": name, "task_id": tid, "cosine": round(cos, 4), "gate": gate,
               "verdict": "PASS" if ok else "LOW", "file": str(dest), "attempts": attempt}
        rec_path.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
        return rec
    rec = {"name": name, "verdict": "FAIL", "file": None, "attempts": 2}
    rec_path.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    return rec


def report() -> None:
    rows = []
    for name in SHOTS:
        p = CANON / f"{name}_state.json"
        rows.append(json.loads(p.read_text(encoding="utf-8")) if p.exists()
                    else {"name": name, "verdict": "PENDING"})
    (CANON / "canonical_report.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    for r in rows:
        print(f"{r['name']:8} {r.get('verdict','?'):7} cos={r.get('cosine','-')}")
    n_pass = sum(1 for r in rows if r.get("verdict") == "PASS")
    print(f"--- {n_pass}/{len(rows)} PASS")


def main() -> None:
    if "--report" in sys.argv:
        report(); return
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    targets = args or list(SHOTS)
    fc = FaceComparator()
    import numpy as np  # noqa: E402
    ref_emb = np.load(IDENT / "ref_embedding.npy")
    for name in targets:
        gen_one(fc, ref_emb, name, SHOTS[name])
    report()


if __name__ == "__main__":
    main()
