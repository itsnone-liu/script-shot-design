# -*- coding: utf-8 -*-
"""couple30 v2.6: B performance track v4 — laughter welded to the ACTION.

User plot note: the laughter must be CAUSED by the quick flip (as in the
original MiniMax take). VLM audit of B_regen3 (2026-09-18):
  ~2.5s  she is ALREADY laughing (face) - no sound there before
  ~3.5s  mid-flip, laughing
  ~5.6-6.8 tangled end-giggle
Fix: place the laugh clip three times across her ACTUAL laughing span:
  2.45s full  |  3.85s -8dB  |  5.90s -11dB (tail giggle)
The flip (~3.5s) falls INSIDE the laughter -> causal beat restored.

Also: audio/bed_room_*.wav - all three segment beds become synthetic room
tone (native-derived beds kept leaking speech murmur through the lowpass:
150-750Hz fundamentals survive an 800Hz lowpass).

Output: audio/segB_perf4.wav
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUD = ROOT / "output" / "creative_v2" / "couple30_v1" / "audio"

LAUGH_AT = [(2400, "-3dB"), (3700, "-5dB"), (5000, "-6dB"), (6300, "-8dB")]
OUT_NAME = "segB_perf5.wav"


def main() -> int:
    l07 = AUD / "_tmp_perf2" / "L07.wav"
    laugh = AUD / "laugh_B.wav"
    cmd = ["ffmpeg", "-y", "-v", "error",
           "-i", str(l07)] + ["-i", str(laugh)] * len(LAUGH_AT) + [
        "-filter_complex",
        "[0:a]aresample=44100,pan=stereo|c0=c0|c1=c0,adelay=300|300[a];"
        + "".join(f"[{i+1}:a]volume={g},adelay={t}|{t}[g{i}];"
                  for i, (t, g) in enumerate(LAUGH_AT))
        + f"[a]{'' .join(f'[g{i}]' for i in range(len(LAUGH_AT)))}"
        f"amix=inputs={1+len(LAUGH_AT)}:normalize=0,"
        "apad=whole_dur=8.000,atrim=0:8.000[m]",
        "-map", "[m]", "-c:a", "pcm_s16le", str(AUD / OUT_NAME)]
    subprocess.run(cmd, check=True)
    print(f"B perf5 -> L07@0.30 + laughs at {[t for t, _ in LAUGH_AT]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
