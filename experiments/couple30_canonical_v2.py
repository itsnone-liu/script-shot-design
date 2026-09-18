# -*- coding: utf-8 -*-
"""C2 身份资产包 · L1 转正组 v2 —— Klein 姿态板 × ReActor 身份回写。2026-09-16。

v1 教训：Klein 指令转正姿态对、身份漂（1/6 过线）。
v2 思路：姿态几何留 Klein 板（canonical/*.png），身份用 ReActor 从原图回写
（inswapper 构造性保身份，concert30 验证路线 swap_face.py reactor 流）。

用法：
    python experiments/couple30_canonical_v2.py            # 全部6角度
    python experiments/couple30_canonical_v2.py front talk  # 指定角度
产物：identity/canonical_v2/{name}.png + canonical_v2_report.json
门禁：front/right34/talk ≥0.55；left34/up/down ≥0.45（inswapper 应显著高于此）
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

import swap_face as sf  # noqa: E402
from experiments.metrics import FaceComparator  # noqa: E402

IDENT = ROOT / "examples" / "couple30_v1" / "identity"
SRC = IDENT / "canonical"
DST = IDENT / "canonical_v2"
REF = IDENT / "ref_original.jpg"
GATE = {"front": 0.55, "right34": 0.55, "talk": 0.55,
        "left34": 0.45, "up": 0.45, "down": 0.45}


def main() -> None:
    names = [a for a in sys.argv[1:]] or list(GATE)
    DST.mkdir(parents=True, exist_ok=True)
    fc = FaceComparator()
    import cv2  # noqa: E402
    import numpy as np  # noqa: E402
    e_ref = fc.embed(fc.largest_face(cv2.imread(str(REF))))
    rows = []
    for name in names:
        plate = SRC / f"{name}.png"
        if not plate.exists():
            rows.append({"name": name, "verdict": "NO_PLATE"}); continue
        tag = f"couple30_canon_v2_{name}"
        meta = sf.run_swap("reactor", plate, REF, tag=tag, max_wait=600)
        files = [Path(f) for f in meta.get("files", [])]
        pngs = [f for f in files if f.suffix.lower() == ".png"] or files
        if not pngs:
            rows.append({"name": name, "verdict": "NO_OUTPUT", "meta_files": [f.name for f in files]})
            continue
        best, best_cos = None, -1.0
        for f in pngs:
            face = fc.largest_face(cv2.imread(str(f)))
            if face is None:
                continue
            cos = float(fc.cosine(fc.embed(face), e_ref))
            if cos > best_cos:
                best, best_cos = f, cos
        if best is None:
            rows.append({"name": name, "verdict": "NO_FACE", "meta_files": [f.name for f in pngs]})
            continue
        dest = DST / f"{name}.png"
        shutil.copy(best, dest)
        gate = GATE[name]
        rows.append({"name": name, "file": str(dest), "source": str(best),
                     "cosine": round(best_cos, 4), "gate": gate,
                     "verdict": "PASS" if best_cos >= gate else "LOW"})
        print(f"[{name}] best cos={best_cos:.4f} gate={gate} -> {dest.name}", flush=True)
    (DST / "canonical_v2_report.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    n_pass = sum(1 for r in rows if r.get("verdict") == "PASS")
    print(f"--- v2: {n_pass}/{len(rows)} PASS")


if __name__ == "__main__":
    main()
