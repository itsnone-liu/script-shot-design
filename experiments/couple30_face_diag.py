# -*- coding: utf-8 -*-
"""Diagnostic: per-face raw W/M scores on a clip (no margin filter)."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "820"))
from experiments.metrics import FaceComparator  # noqa: E402

IDENT = ROOT / "examples" / "couple30_v1" / "identity"
KF = ROOT / "examples" / "couple30_v1" / "keyframes"
W_REFS = [IDENT / "refs_extra" / "ref03.jpg", IDENT / "canonical_v6" / "front.png"]
M_REFS = [KF / "KF_M.png"]


def main() -> None:
    clip = Path(sys.argv[1])
    fc = FaceComparator()
    det = cv2.FaceDetectorYN.create(str(ROOT.parent / "820" / "data" / "models" / "yunet.onnx"),
                                    "", (672, 896), score_threshold=0.6)
    cap = cv2.VideoCapture(str(clip))
    vfps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    tmp = Path(tempfile.gettempdir()) / "diag_face.jpg"
    n = 0
    while True:
        ok, im = cap.read()
        if not ok:
            break
        n += 1
        if n % max(1, round(vfps / 2)):
            continue
        h, w = im.shape[:2]
        det.setInputSize((w, h))
        _, faces = det.detect(im)
        t = n / vfps
        if faces is None:
            print(f"t={t:.2f} no faces")
            continue
        for i, f in enumerate(faces):
            x, y, fw, fh = (int(v) for v in f[:4])
            conf = float(f[-1])
            crop = cv2.cvtColor(im[y:y + fh, x:x + fw], cv2.COLOR_BGR2GRAY)
            sharp = float(cv2.Laplacian(crop, cv2.CV_64F).var())
            scale = 1.4
            cx, cy = x + fw / 2, y + fh / 2
            x0 = max(0, int(cx - fw * scale / 2)); y0 = max(0, int(cy - fh * scale / 2))
            fimg = im[y0:min(h, y0 + int(fh * scale)), x0:min(w, x0 + int(fw * scale))]
            cv2.imwrite(str(tmp), fimg)
            wv = [fc.score(str(tmp), str(p))["cosine"] for p in W_REFS
                  if fc.score(str(tmp), str(p)).get("face_ok")]
            mv = [fc.score(str(tmp), str(p))["cosine"] for p in M_REFS
                  if fc.score(str(tmp), str(p)).get("face_ok")]
            print(f"t={t:.2f} face{i} y={cy/h:.2f} conf={conf:.2f} sharp={sharp:.0f} "
                  f"W={[round(v,3) for v in wv]} M={[round(v,3) for v in mv]}")
    cap.release()


if __name__ == "__main__":
    main()
