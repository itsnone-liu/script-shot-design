# -*- coding: utf-8 -*-
"""couple30 v2.7 helper: direct B_regen4 repair, bypassing the probe matrix.

Rationale: probes timed out on a transient HTTP error; the last three B
takes all picked idx1/no. Direct repair with that config, measure, retime
(ReActor output carries the 12fps tag -> itsscale 0.5 + fps=24).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

import couple30_repair as rep  # noqa: E402


def main() -> int:
    outdir = ROOT / "output" / "creative_v2" / "couple30_v1" / "repaired"
    # optional argv: src_name tag (default: B_regen4_00 r_B4)
    src_name = sys.argv[1] if len(sys.argv) > 1 else "B_regen4_00.mp4"
    tag = sys.argv[2] if len(sys.argv) > 2 else "r_B4"
    stem = src_name.rsplit("_00", 1)[0]
    src = outdir / src_name
    dest = outdir / f"{stem}_repaired.mp4"
    outs = rep.run_reactor(src, 1, tag, gender="no")
    if not outs:
        raise SystemExit("no outputs")
    mp4 = next((u for u in outs if str(u).lower().endswith(".mp4")), outs[0])
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    f"Copy-Item '{mp4}' '{dest}' -Force"], check=True)
    m = rep.measure(dest)
    print(stem, "repaired measure:", json.dumps(m, ensure_ascii=False))
    # retime if 12fps tag
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v",
                        "-show_entries", "stream=r_frame_rate", "-of",
                        "csv=p=0", str(dest)], capture_output=True, text=True)
    if r.stdout.strip().startswith("12/"):
        tmp = str(dest) + ".tmp.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-itsscale", "0.5",
                        "-i", str(dest), "-vf", "fps=24", "-c:v", "libx264",
                        "-preset", "slow", "-crf", "16", "-pix_fmt",
                        "yuv420p", "-an", tmp], check=True)
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        f"Move-Item '{tmp}' '{dest}' -Force"], check=True)
        print("retimed to 24fps")
    r2 = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                         "format=duration", "-of", "csv=p=0", str(dest)],
                        capture_output=True, text=True)
    print("final dur:", r2.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
