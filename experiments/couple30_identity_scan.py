# -*- coding: utf-8 -*-
"""couple30 identity scan — free local pre-repair measurement on selected takes.

For A_T1 / B_T2 / C_T2: per sampled frame, detect faces (YuNet), score each clear
face against W anchors (canonical_v6 front + ref03 + angle-matched up/down/talk)
and M anchor (KF_M), classify faces by argmax margin, track W's vertical rank.
Output: per-segment identity baseline + W position windows (for repair windowing).

Usage:
  python -X utf8 experiments/couple30_identity_scan.py [--fps 2]
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "820"))
from experiments.metrics import FaceComparator  # noqa: E402

IDENT = ROOT / "examples" / "couple30_v1" / "identity"
KF = ROOT / "examples" / "couple30_v1" / "keyframes"
SHOTS = ROOT / "output" / "creative_v2" / "couple30_v1" / "shots"
OUT = ROOT / "output" / "creative_v2" / "couple30_v1" / "identity_scan"

W_REFS = [
    IDENT / "refs_extra" / "ref03.jpg",          # identity center (real photo)
    IDENT / "canonical_v6" / "front.png",         # approved final front
    IDENT / "canonical_v6" / "talk.png",          # mouth-open anchor
    IDENT / "canonical_v6" / "up.png",            # C-segment chin-up anchor
    IDENT / "canonical_v6" / "down.png",          # A-segment俯角 anchor
]
M_REFS = [KF / "KF_M.png"]

TAKES = {
    "A": SHOTS / "C30_A_T1_00.mp4",
    "B": SHOTS / "C30_B_T2_00.mp4",
    "C": SHOTS / "C30_C_T2_00.mp4",
}

YUNET = ROOT.parent / "820" / "data" / "models" / "yunet.onnx"


def scan(clip: Path, fc: FaceComparator, fps: float) -> dict:
    cap = cv2.VideoCapture(str(clip))
    vfps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    det = cv2.FaceDetectorYN.create(str(YUNET), "", (672, 896), score_threshold=0.7)
    rows = []
    idx = 0
    import tempfile
    tmp = Path(tempfile.gettempdir()) / "c30_scan_face.jpg"
    while True:
        ok, im = cap.read()
        if not ok:
            break
        step = max(1, round(vfps / fps))
        if idx % step:
            idx += 1
            continue
        h, w = im.shape[:2]
        det.setInputSize((w, h))
        _, faces = det.detect(im)
        t = idx / vfps
        row = {"t": round(t, 2), "faces": []}
        if faces is not None:
            for f in faces:
                x, y, fw, fh = (int(v) for v in f[:4])
                conf = float(f[-1])
                if conf < 0.8 or fh < 40:
                    continue
                crop = cv2.cvtColor(im[y:y + fh, x:x + fw], cv2.COLOR_BGR2GRAY)
                sharp = float(cv2.Laplacian(crop, cv2.CV_64F).var())
                if sharp < 50:
                    continue
                scale = 1.4
                cx, cy = x + fw / 2, y + fh / 2
                x0 = max(0, int(cx - fw * scale / 2)); y0 = max(0, int(cy - fh * scale / 2))
                fimg = im[y0:min(h, y0 + int(fh * scale)), x0:min(w, x0 + int(fw * scale))]
                cv2.imwrite(str(tmp), fimg)
                wv = [r["cosine"] for p in W_REFS
                      for r in [fc.score(str(tmp), str(p))]
                      if r.get("face_ok") and r.get("cosine") is not None]
                mv = [r["cosine"] for p in M_REFS
                      for r in [fc.score(str(tmp), str(p))]
                      if r.get("face_ok") and r.get("cosine") is not None]
                row["faces"].append({
                    "y_center": round(cy / h, 3), "area": fw * fh,
                    "w": round(max(wv), 4) if wv else None,
                    "m": round(max(mv), 4) if mv else None,
                    "sharp": round(sharp, 1),
                })
        rows.append(row)
        idx += 1
    cap.release()

    # classify faces: W if w>m (margin>=0.05), track W vertical rank
    w_scores, w_rows = [], []
    for row in rows:
        ws = [f for f in row["faces"] if f["w"] is not None and f["m"] is not None
              and f["w"] - f["m"] >= 0.05]
        row["w_faces"] = len(ws)
        row["m_faces"] = len([f for f in row["faces"] if f["w"] is not None
                              and f["m"] is not None and f["m"] - f["w"] >= 0.05])
        if ws:
            best = max(ws, key=lambda f: f["w"])
            row["w_best"] = best["w"]
            others = [f for f in row["faces"] if f is not best]
            row["w_rank_top"] = all(best["y_center"] <= f["y_center"] + 0.02 for f in others)
            w_scores.append(best["w"])
        w_rows.append({k: row.get(k) for k in ("t", "w_faces", "m_faces", "w_best", "w_rank_top")})

    vals = w_scores
    rep = {
        "clip": str(clip), "sampled": len(rows), "w_samples": len(vals),
        "w_median": round(statistics.median(vals), 4) if vals else None,
        "w_min": round(min(vals), 4) if vals else None,
        "w_gate_060": ("PASS" if vals and statistics.median(vals) >= 0.60 and min(vals) >= 0.50 else "FAIL"),
        "frames": w_rows,
    }
    return rep


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    fc = FaceComparator()
    report = {}
    for seg, clip in TAKES.items():
        if not clip.exists():
            print(f"[{seg}] missing {clip}")
            continue
        rep = scan(clip, fc, fps=2.0)
        report[seg] = rep
        top = min(30, len(rep["frames"]))
        print(f"== {seg}: w_median={rep['w_median']} w_min={rep['w_min']} gate={rep['w_gate_060']}")
        for r in rep["frames"][:top]:
            mark = "TOP" if r.get("w_rank_top") else "bot"
            print(f"   t={r['t']:>6} faces(W/M)={r['w_faces']}/{r['m_faces']} w={r.get('w_best')} pos={mark}")
    dest = OUT / "identity_scan_report.json"
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved ->", dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
