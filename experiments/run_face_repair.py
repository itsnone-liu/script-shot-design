# -*- coding: utf-8 -*-
"""Role-isolated video face repair via ReActor workflow 2005804455352303618.
Replaces faces in a generated plate with a real person's face, preserving action/lighting.

Usage:
  python experiments/run_face_repair.py <plate.mp4> <source_face.jpg> <out_prefix> [face_index]
face_index: which detected face to swap (0 = largest/primary, 1 = second). Default 0.
Chained two-person repair: pass A swaps face 0 with singer crop, then pass B on pass A's
output swaps face 1 with girl crop (or vice versa per detection order).
Paid task; respects production_plan_v2.json paid_generation_locked.
"""
from __future__ import annotations
import json, sys, time, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / '820'))
from experiments import rh_task

ROOT = Path(__file__).resolve().parents[1]
FMT = ROOT.parent / '820' / 'data' / 'api_format' / '2005804455352303618.json'
CARRIER = '2093518439926218753'  # in-account workflow id used as API carrier (workflow param overrides content)

def wait_tolerant(key, tid, prefix, max_wait=2400):
    """Poll outputs endpoint tolerantly: HTTP 500 happens while the task is still running."""
    deadline = time.time() + max_wait
    last = ''
    while time.time() < deadline:
        try:
            out = rh_task.task_outputs(key, tid)
            return out
        except Exception as e:
            msg = f'{type(e).__name__}: {str(e)[:100]}'
            if msg != last: print(f'[{prefix}] {msg}', flush=True); last = msg
            time.sleep(30)
    raise SystemExit(f'[{prefix}] timeout waiting for {tid}')

def repair(plate: Path, face: Path, prefix: str, face_index: int = 0) -> dict:
    plan = json.loads((ROOT/'examples'/'concert30_hcy_flowers'/'production_plan_v2.json').read_text(encoding='utf-8'))
    if plan.get('paid_generation_locked'): raise SystemExit('REFUSED: paid_generation_locked')
    fmt = json.loads(FMT.read_text(encoding='utf-8'))
    key = rh_task.load_api_key()
    u_face = rh_task.upload_file(key, face)
    u_vid = rh_task.upload_file(key, plate)
    print(f'[{prefix}] face(idx {face_index}) -> {u_face}\n[{prefix}] plate -> {u_vid}', flush=True)
    fmt['10']['inputs']['image'] = u_face
    fmt['11']['inputs']['video'] = u_vid
    fmt['15']['inputs']['input_faces_index'] = str(face_index)
    fmt['18']['inputs']['save_output'] = True
    fmt['21']['inputs']['save_output'] = False  # comparison video not needed as artifact
    tid = rh_task.run_workflow_json(key, fmt, sandbox_id=CARRIER)
    print(f'[{prefix}] task {tid}', flush=True)
    out = ROOT/'output'/'concert30_hcy_flowers_v2'/'repaired'; out.mkdir(parents=True, exist_ok=True)
    result = wait_tolerant(key, tid, prefix)
    records = []
    for n, u in enumerate(rh_task.collect_file_urls(result)):
        ext = '.zip' if '.zip' in u.lower() else '.mp4'
        target = out/f'{prefix}_{n:02d}{ext}'; rh_task.download(u, target); records.append(str(target))
        if ext == '.zip':
            with zipfile.ZipFile(target) as z: z.extractall(out/f'{prefix}_unzipped')
    state = {'prefix': prefix, 'task_id': tid, 'face_index': face_index, 'outputs': records}
    (out/f'{prefix}_state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return state

if __name__ == '__main__':
    repair(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 0)
