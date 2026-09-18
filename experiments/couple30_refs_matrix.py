# -*- coding: utf-8 -*-
"""couple30_refs_matrix.py — 7 张参考图 SFace 交叉矩阵 + 检测质量。"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "820"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "820" / "experiments"))
import cv2  # noqa: E402
import numpy as np  # noqa: E402
from experiments.metrics import FaceComparator  # noqa: E402

IDENT = ROOT / "examples" / "couple30_v1" / "identity"
REFS = [("ref01", IDENT / "ref_original.jpg")] + [
    (f"ref{n:02d}", p) for n, p in enumerate(sorted((IDENT / "refs_extra").glob("ref*.jpg")), start=2)]

fc = FaceComparator()
embs, meta = {}, {}
for name, path in REFS:
    img = cv2.imread(str(path))
    h, w = img.shape[:2]
    det = fc.det
    det.setInputSize((w, h))
    _, faces = det.detect(img)
    if faces is None or len(faces) == 0:
        print(f"{name}: NO FACE")
        continue
    areas = faces[:, 2] * faces[:, 3]
    i = int(np.argmax(areas))
    f = faces[i]
    embs[name] = fc.embed(fc.rec.alignCrop(img, f))
    meta[name] = {"size": int(f[2] * f[3]), "score": round(float(f[14]), 3),
                  "n_faces": int(len(faces)), "box": [round(float(v)) for v in f[:4]]}
    print(f"{name}: face {int(f[2])}x{int(f[3])} score={float(f[14]):.2f} n={len(faces)}")

names = list(embs)
print("\n=== cosine matrix ===")
hdr = "      " + " ".join(f"{n[-2:]}   " for n in names)
print(hdr)
avg = {}
for a in names:
    row = []
    tot = 0.0
    for b in names:
        c = fc.cosine(embs[a], embs[b]) if a != b else 1.0
        tot += c if a != b else 0
        row.append(c)
    avg[a] = tot / (len(names) - 1)
    print(f"{a[-2:]}  " + " ".join(f"{c:+.2f}" for c in row) + f"   avg={avg[a]:.3f}")

print("\n=== centrality ranking (avg sim to others; higher = more typical) ===")
for n in sorted(names, key=lambda x: -avg[x]):
    m = meta[n]
    print(f"{n}  avg={avg[n]:.3f}  facesize={m['size']}  det={m['score']}")

out = {"matrix": {a: {b: round(float(fc.cosine(embs[a], embs[b])), 4) for b in names} for a in names},
       "meta": meta, "avg": {k: round(v, 4) for k, v in avg.items()}}
(IDENT / "refs_matrix.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print("\nsaved refs_matrix.json")
