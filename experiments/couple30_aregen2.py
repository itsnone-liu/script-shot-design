# -*- coding: utf-8 -*-
"""couple30 A-segment route-乙 v2: SPLIT-HALF regeneration.

v1 (single 15s run, webapp 2095531397845889025) failed: endpoints locked but the
free middle drifted to an unrelated tea-table scene at ~5-11s. Fix: split A into
two 7.5s halves, each with REAL take frames as both anchors:
  part1: KF_A1_corrected -> A_T1@7.5s frame   + audio L01-L03 (7.5s)
  part2: A_T1@7.5s frame -> KF_A_LAST_corrected + audio L04-L06 (7.5s)
Shorter free middle = less drift room; real-frame mid anchor = scene continuity.
Output stitched locally -> A_regen2.mp4, identity-measured.

Usage: python -X utf8 experiments/couple30_aregen2.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "820"))
sys.path.insert(0, str(ROOT / "experiments"))

from experiments import rh_task  # noqa: E402
import couple30_repair as rep  # noqa: E402

KF = ROOT / "examples" / "couple30_v1" / "keyframes"
AUD = ROOT / "output" / "creative_v2" / "couple30_v1" / "audio"
A_TAKE = ROOT / "output" / "creative_v2" / "couple30_v1" / "shots" / "C30_A_T1_00.mp4"
OUT = rep.OUT
APP = "2095531397845889025"
STATE = OUT / "aregen2_state.json"


def run_part(tag: str, first: Path, last: Path, audio: Path, dest: Path) -> None:
    key = rh_task.load_api_key()
    node_info = [
        {"nodeId": "72", "fieldName": "image", "fieldValue": rh_task.upload_file(key, first)},
        {"nodeId": "93", "fieldName": "image", "fieldValue": rh_task.upload_file(key, last)},
        {"nodeId": "74", "fieldName": "audio", "fieldValue": rh_task.upload_file(key, audio)},
    ]
    tid = rh_task.run_webapp(key, APP, node_info)
    print(f"[{tag}] task {tid}", flush=True)
    result = None
    deadline = time.time() + 2700
    while time.time() < deadline:
        try:
            result = rh_task.task_outputs(key, tid)
            break
        except Exception as e:
            print(f"[{tag}] poll: {type(e).__name__}: {str(e)[:80]}", flush=True)
            time.sleep(30)
    if result is None:
        raise SystemExit(f"[{tag}] timeout")
    urls = rh_task.collect_file_urls(result)
    if not urls:
        raise SystemExit(f"[{tag}] no outputs")
    rh_task.download(urls[0], dest)
    print(f"[{tag}] -> {dest}", flush=True)


def main() -> int:
    st = json.loads(STATE.read_text(encoding="utf-8-sig")) if STATE.exists() else {}
    mid = OUT / "A_mid_anchor.png"
    if not mid.exists():
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "7.5", "-i", str(A_TAKE),
                        "-frames:v", "1", str(mid)], check=True)
    p1_a = AUD / "aregen2_p1.wav"
    p2_a = AUD / "aregen2_p2.wav"
    tl = json.loads((AUD / "segA_timeline.json").read_text(encoding="utf-8"))
    # audio halves: L01-L03 (through ~8.7s) / L04-L06
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(AUD / "segA_dialogue.wav"),
                    "-t", "7.5", str(p1_a)], check=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "7.5",
                    "-i", str(AUD / "segA_dialogue.wav"), str(p2_a)], check=True)

    d1, d2 = OUT / "A_regen2_p1.mp4", OUT / "A_regen2_p2.mp4"
    if not d1.exists():
        run_part("p1", KF / "KF_A1_corrected.png", mid, p1_a, d1)
    if not d2.exists():
        run_part("p2", mid, KF / "KF_A_LAST_corrected.png", p2_a, d2)

    dest = OUT / "A_regen2.mp4"
    if not dest.exists():
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(d1), "-i", str(d2)]
        cmd += ["-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]",
                "-c:v", "libx264", "-preset", "slow", "-crf", "16",
                "-pix_fmt", "yuv420p", "-an", str(dest)]
        subprocess.run(cmd, check=True)
    m = rep.measure(dest)
    st.update({"output": str(dest), "measure": m})
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    print("A_regen2 measure:", json.dumps(m, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
