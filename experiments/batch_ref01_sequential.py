# -*- coding: utf-8 -*-
"""Sequential driver: run remaining ref01-source repairs + S2 regen one at a time,
retrying on [421] TASK_QUEUE_MAXED with backoff. Skips jobs whose output already exists."""
from __future__ import annotations
import subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REP = ROOT / 'output' / 'concert30_hcy_flowers_v2' / 'repaired'
SHOTS = ROOT / 'output' / 'concert30_hcy_flowers_v2' / 'shots'
PY = r'D:\uv\python\cpython-3.11-windows-x86_64-none\python.exe'
REF01 = str(ROOT / 'examples' / 'concert30_hcy_flowers' / 'refs_hcy_v2' / 'ref01_crop.jpg')

REPAIRS = [
    # (plate, prefix, face_index)  — all with ref01 source
    (SHOTS / 'S3v3_plate.mp4', 'S3ab', 0),
    (SHOTS / 'S4v3_subB.mp4', 'S4ab_B', 1),
    (SHOTS / 'S4v3_subC.mp4', 'S4ab_C', 0),
    (SHOTS / 'S6v3_subA.mp4', 'S6ab_A_G', 1),
    (SHOTS / 'S6v3_subB.mp4', 'S6ab_B', 0),
]
REGEN = ['S2']

def exists(prefix):
    return next(REP.glob(f'{prefix}_*.mp4'), None) is not None

def run_retry(args, label, max_tries=30, backoff=60):
    for attempt in range(1, max_tries + 1):
        r = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if r.returncode == 0:
            print(f'[driver] {label} OK', flush=True)
            return True
        err = (r.stderr or '') + (r.stdout or '')
        if 'TASK_QUEUE_MAXED' in err or '421' in err:
            print(f'[driver] {label} queue maxed (attempt {attempt}), sleep {backoff}s', flush=True)
            time.sleep(backoff)
            continue
        print(f'[driver] {label} FAILED rc={r.returncode}\n{err[-1500:]}', flush=True)
        return False
    return False

def main():
    for prefix_only in [p for _, p, _ in REPAIRS]:
        pass
    for plate, prefix, idx in REPAIRS:
        if exists(prefix):
            print(f'[driver] skip {prefix} (exists)', flush=True)
            continue
        ok = run_retry([PY, '-X', 'utf8', str(ROOT / 'experiments' / 'run_face_repair.py'),
                        str(plate), REF01, prefix, str(idx)], f'repair:{prefix}')
        if not ok:
            print(f'[driver] {prefix} left incomplete', flush=True)
    if not (SHOTS / 'S2_state.json').exists() or True:
        # S2 regen always attempted only if no fresh v4 output marker
        marker = SHOTS / 'S2v4.done'
        if marker.exists():
            print('[driver] skip S2 regen (done)', flush=True)
        else:
            ok = run_retry([PY, '-X', 'utf8', str(ROOT / 'experiments' / 'run_concert30_v2_ref2va.py'), '--run', 'S2'], 'regen:S2')
            if ok:
                marker.touch()
    print('[driver] batch complete', flush=True)

if __name__ == '__main__':
    main()
