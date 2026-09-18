# -*- coding: utf-8 -*-
"""couple30 A-segment route-乙: audio-driven first/last-frame H3 regeneration.

Replaces A's native-audio take with a lip-synced regeneration:
  first frame = KF_A1_corrected.png (approved composition+identity)
  last frame  = KF_A_LAST_corrected.png
  drive audio = segA_dialogue.wav (15s, 6 turns W+M)
Webapp 2095531397845889025 (nodes 72/93/74/78). Output measured locally with
the same identity gate as the repair chain.

Usage: python -X utf8 experiments/couple30_aregen.py [--skip-if-done]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "820"))
sys.path.insert(0, str(ROOT / "experiments"))

from experiments import rh_task  # noqa: E402
import couple30_repair as rep  # noqa: E402

KF = ROOT / "examples" / "couple30_v1" / "keyframes"
AUDIO = ROOT / "output" / "creative_v2" / "couple30_v1" / "audio"
OUT = rep.OUT
APP = "2095531397845889025"
STATE = OUT / "aregen_state.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-if-done", action="store_true")
    args = ap.parse_args()
    st = json.loads(STATE.read_text(encoding="utf-8-sig")) if STATE.exists() else {}
    if args.skip_if_done and st.get("output"):
        print("already done:", st["output"])
        return 0

    key = rh_task.load_api_key()
    u_first = rh_task.upload_file(key, KF / "KF_A1_corrected.png")
    u_last = rh_task.upload_file(key, KF / "KF_A_LAST_corrected.png")
    u_audio = rh_task.upload_file(key, AUDIO / "segA_dialogue.wav")
    print(f"first={u_first}\nlast={u_last}\naudio={u_audio}", flush=True)

    node_info = [
        {"nodeId": "72", "fieldName": "image", "fieldValue": u_first},
        {"nodeId": "93", "fieldName": "image", "fieldValue": u_last},
        {"nodeId": "74", "fieldName": "audio", "fieldValue": u_audio},
    ]
    tid = rh_task.run_webapp(key, APP, node_info)
    print(f"task {tid}", flush=True)
    st["task"] = tid
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")

    deadline = time.time() + 3600
    result = None
    while time.time() < deadline:
        try:
            result = rh_task.task_outputs(key, tid)
            break
        except Exception as e:
            print(f"poll: {type(e).__name__}: {str(e)[:90]}", flush=True)
            time.sleep(30)
    if result is None:
        raise SystemExit("timeout waiting for aregen task")
    urls = rh_task.collect_file_urls(result)
    if not urls:
        raise SystemExit("no output files")
    dest = OUT / "A_regen_00.mp4"
    rh_task.download(urls[0], dest)
    print("downloaded ->", dest)

    m = rep.measure(dest)
    st.update({"output": str(dest), "measure": m})
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    print("identity measure:", json.dumps(m, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
