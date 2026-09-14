# -*- coding: utf-8 -*-
"""Identity QA gate for concert30 v2 clips: clear-face classification + role medians + cross-ID margin.

Usage (ComfyUI embedded python):
  python experiments/qa_identity.py <clip.mp4> girl|hua|both [--outdir DIR]

Clear-face rule: YuNet confidence >= 0.85 AND face height >= 48 px (768p frame) AND Laplacian variance of face crop >= 60.
Gate (delivery_identity_gate in segments_v2.json): per-role clear-face median >= 0.60, floor >= 0.50, cross-ID margin >= 0.12.
"""
from __future__ import annotations
import json, statistics, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'examples' / 'concert30_hcy_flowers'
GIRL_REFS = [BASE/'refs_hcy_v2'/'G_ref06_direct_facecrop_PASS.jpg', BASE/'refs'/'ref05_dessert_tshirt.jpg',
             BASE/'refs'/'ref03_stadium_selfie.jpg', BASE/'refs'/'ref04_theater_hoodie.jpg']
HUA_REFS = [BASE/'refs_hcy_v2'/'H1_front_natural_PASS.jpg', BASE/'refs_hcy_v2'/'H2_left_threequarter_PASS.jpg',
            BASE/'refs_hcy_v2'/'H4_singing_openmouth_PASS.jpg']

def frames_from(clip: Path, fps=2):
    import cv2
    cap = cv2.VideoCapture(str(clip)); n = 0
    while True:
        ok, im = cap.read()
        if not ok: break
        n += 1
        if n % max(1, round(cap.get(cv2.CAP_PROP_FPS)/fps)) == 0:
            yield im
    cap.release()

def main():
    clip = Path(sys.argv[1]); role = sys.argv[2] if len(sys.argv) > 2 else 'girl'
    import cv2, numpy as np
    sys.path.insert(0, str(ROOT.parent/'820'))
    from experiments.metrics import FaceComparator
    fc = FaceComparator()
    det = cv2.FaceDetectorYN.create(str(ROOT.parent/'820'/'data'/'models'/'yunet.onnx'), '', (1344, 768), score_threshold=0.7)
    refs = {'girl': GIRL_REFS, 'hua': HUA_REFS}
    roles = [role] if role != 'both' else ['girl', 'hua']
    rows = []
    for im in frames_from(clip):
        h, w = im.shape[:2]; det.setInputSize((w, h))
        _, faces = det.detect(im)
        clear = []
        if faces is not None:
            for f in faces:
                x, y, fw, fh = (int(v) for v in f[:4]); conf = float(f[-1])
                if conf < 0.85 or fh < 48: continue
                crop = cv2.cvtColor(im[y:y+fh, x:x+fw], cv2.COLOR_BGR2GRAY)
                sharp = float(cv2.Laplacian(crop, cv2.CV_64F).var())
                if sharp < 60: continue
                clear.append((fw*fh, x, y, fw, fh))
        clear.sort(reverse=True); clear = clear[:2]  # protagonist is among the two largest clear faces
        row = {'clear_face': bool(clear), 'n_clear': len(clear)}
        for area, x, y, fw, fh in clear:
            scale = 1.5; cx, cy = x+fw/2, y+fh/2
            x0, y0 = max(0, int(cx-fw*scale/2)), max(0, int(cy-fh*scale/2))
            fimg = im[y0:min(im.shape[0], y0+int(fh*scale)), x0:min(im.shape[1], x0+int(fw*scale))]
            tmp = Path(tempfile.gettempdir())/'qa_face.jpg'; cv2.imwrite(str(tmp), fimg)
            for r in roles:
                s = [fc.score(str(tmp), str(p)) for p in refs[r]]
                v = [t['cosine'] for t in s if t.get('face_ok') and t.get('cosine') is not None]
                if v:
                    m = round(max(v), 4)
                    key = f'{r}_max'
                    if row.get(key) is None or m > row[key]: row[key] = m
        rows.append(row)
    out = {'clip': str(clip), 'sampled': len(rows), 'roles': roles, 'frames': rows}
    for r in roles:
        vals = [x[f'{r}_max'] for x in rows if x.get('clear_face') and x.get(f'{r}_max') is not None]
        out[f'{r}_clear_faces'] = len(vals)
        if vals:
            out[f'{r}_median'] = round(statistics.median(vals), 4); out[f'{r}_min'] = round(min(vals), 4)
            out[f'{r}_gate'] = 'PASS' if statistics.median(vals) >= 0.60 and min(vals) >= 0.50 else 'FAIL'
    if role == 'both':
        m = [x['girl_max']-x['hua_max'] for x in rows if x.get('clear_face') and x.get('girl_max') is not None and x.get('hua_max') is not None]
        if m: out['cross_id_margin_min'] = round(min(m), 4); out['cross_id_gate'] = 'PASS' if min(m) >= 0.12 else 'FAIL'
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__': raise SystemExit(main())
