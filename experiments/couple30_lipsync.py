# -*- coding: utf-8 -*-
"""couple30 route-甲 lipsync: windowed LatentSync on the repaired C segment.

Feeds the STITCHED C (passthrough head + repaired tail), pads L10.wav with
leading silence to its timeline offset inside the integer-second window, runs
webapp 2086650291638005762 (nodes 308 video / 125 audio / 327 start / 328 end /
324 fps=24), downloads output. Target face = W (chin-up under M at ~4.4-6.9s);
verify visually — if M's mouth moved instead, switch to multi-person webapp
2086650599655108610 with explicit face index.

Usage: python -X utf8 experiments/couple30_lipsync.py [--start 4 --end 7]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "820"))

from experiments import rh_task  # noqa: E402

AUDIO = ROOT / "output" / "creative_v2" / "couple30_v1" / "audio"
OUT = ROOT / "output" / "creative_v2" / "couple30_v1" / "repaired"
APP = "2086650291638005762"
STATE = OUT / "lipsync_state.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", type=Path, default=OUT / "C_repaired.mp4")
    ap.add_argument("--line", default="L10")
    ap.add_argument("--start", type=int, default=4)
    ap.add_argument("--end", type=int, default=7)
    args = ap.parse_args()
    st = json.loads(STATE.read_text(encoding="utf-8-sig")) if STATE.exists() else {}

    tl = json.loads((AUDIO / "segC_timeline.json").read_text(encoding="utf-8"))
    ln = next(x for x in tl if x["id"] == args.line)
    pad_ms = int(round(max(0.0, ln["start"] - args.start) * 1000))
    padded = AUDIO / f"{args.line}_pad.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(AUDIO / f"{args.line}.wav"),
                    "-af", f"adelay={pad_ms}|{pad_ms}", str(padded)], check=True)
    print(f"{args.line} window=[{args.start},{args.end}] pad={pad_ms}ms dur={ln['dur']}s")

    key = rh_task.load_api_key()
    u_vid = rh_task.upload_file(key, args.video)
    u_aud = rh_task.upload_file(key, padded)
    print(f"video={u_vid}\naudio={u_aud}", flush=True)
    node_info = [
        {"nodeId": "308", "fieldName": "video", "fieldValue": u_vid},
        {"nodeId": "125", "fieldName": "audio", "fieldValue": u_aud},
        {"nodeId": "327", "fieldName": "value", "fieldValue": str(args.start)},
        {"nodeId": "328", "fieldName": "value", "fieldValue": str(args.end)},
        {"nodeId": "324", "fieldName": "value", "fieldValue": "24"},
    ]
    tid = rh_task.run_webapp(key, APP, node_info)
    print(f"task {tid}", flush=True)
    st["task"] = tid
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")

    result = None
    deadline = time.time() + 2400
    while time.time() < deadline:
        try:
            result = rh_task.task_outputs(key, tid)
            break
        except Exception as e:
            print(f"poll: {type(e).__name__}: {str(e)[:90]}", flush=True)
            time.sleep(30)
    if result is None:
        raise SystemExit("timeout waiting for lipsync task")
    urls = rh_task.collect_file_urls(result)
    if not urls:
        raise SystemExit("no output files")
    dest = OUT / "C_lipsync_00.mp4"
    rh_task.download(urls[0], dest)
    st["output"] = str(dest)
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    print("downloaded ->", dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
