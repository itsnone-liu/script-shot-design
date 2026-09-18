# -*- coding: utf-8 -*-
"""couple30 C lipsync fallback: whole-clip LatentSync1.6 (webapp 2076998668398784513).

The windowed webapp (2086650291638005762) task errored server-side (805). Fallback:
cut C_repaired [4,7]s -> 3s clip, lipsync the whole clip with L10 padded audio,
stitch back -> C_lipsync.mp4.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "820"))

from experiments import rh_task  # noqa: E402

REP = ROOT / "output" / "creative_v2" / "couple30_v1" / "repaired"
AUD = ROOT / "output" / "creative_v2" / "couple30_v1" / "audio"
APP = "2076998668398784513"
STATE = REP / "lipsync_state.json"


def main() -> int:
    seg_in = REP / "c_lips_in.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "4.0", "-to", "7.0",
                    "-i", str(REP / "C_repaired.mp4"), "-c:v", "libx264", "-crf", "16",
                    "-pix_fmt", "yuv420p", "-an", str(seg_in)], check=True)
    key = rh_task.load_api_key()
    u_v = rh_task.upload_file(key, seg_in)
    u_a = rh_task.upload_file(key, AUD / "L10_pad.wav")
    print(f"video={u_v}\naudio={u_a}", flush=True)
    node_info = [
        {"nodeId": "5", "fieldName": "video", "fieldValue": u_v},
        {"nodeId": "14", "fieldName": "audio", "fieldValue": u_a},
    ]
    tid = rh_task.run_webapp(key, APP, node_info)
    print(f"task {tid}", flush=True)
    result = None
    deadline = time.time() + 1800
    while time.time() < deadline:
        try:
            result = rh_task.task_outputs(key, tid)
            break
        except Exception as e:
            msg = f"{type(e).__name__}: {str(e)[:80]}"
            if "STATUS_ERROR" in msg:
                raise SystemExit(f"task failed server-side: {msg}")
            print(f"poll: {msg}", flush=True)
            time.sleep(30)
    if result is None:
        raise SystemExit("timeout")
    urls = rh_task.collect_file_urls(result)
    if not urls:
        raise SystemExit("no outputs")
    mid = REP / "c_lips_mid_00.mp4"
    rh_task.download(urls[0], mid)
    print("mid ->", mid)

    # fps normalize RH output then stitch: [0,4] + mid + [7,13.5]
    import re
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v",
                        "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", str(mid)],
                       capture_output=True, text=True)
    m = re.match(r"(\d+)/(\d+)", r.stdout.strip())
    scale = []
    if m:
        fps = int(m.group(1)) / int(m.group(2))
        if 1 < fps < 20:
            scale = ["-itsscale", f"{fps / 24:.6f}"]
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(REP / "C_repaired.mp4"),
                    *scale, "-i", str(mid)],
                   check=False)
    # cut head/tail of C_repaired and concat 3 parts
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "0", "-to", "4.0",
                    "-i", str(REP / "C_repaired.mp4"), "-c:v", "libx264", "-crf", "16",
                    "-an", str(REP / "c_lips_head.mp4")], check=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "7.0",
                    "-i", str(REP / "C_repaired.mp4"), "-c:v", "libx264", "-crf", "16",
                    "-an", str(REP / "c_lips_tail.mp4")], check=True)
    cmd = ["ffmpeg", "-y", "-v", "error",
           "-i", str(REP / "c_lips_head.mp4"), *scale, "-i", str(mid),
           "-i", str(REP / "c_lips_tail.mp4")]
    cmd += ["-filter_complex",
            "[0:v]fps=24[h];[1:v]fps=24[m];[2:v]fps=24[t];[h][m][t]concat=n=3:v=1:a=0[v]",
            "-map", "[v]", "-c:v", "libx264", "-preset", "slow", "-crf", "16",
            "-pix_fmt", "yuv420p", "-an", str(REP / "C_lipsync_00.mp4")]
    r = subprocess.run(cmd)
    if r.returncode and not (REP / "C_lipsync_00.mp4").exists():
        raise SystemExit("final stitch failed")
    st = json.loads(STATE.read_text(encoding="utf-8-sig")) if STATE.exists() else {}
    st["output"] = str(REP / "C_lipsync_00.mp4")
    st["app"] = APP
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    print("done ->", st["output"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
