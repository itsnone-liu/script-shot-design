# -*- coding: utf-8 -*-
"""couple30 v2.8: drive B with the ORIGINAL natural laugh performance.

User: "四段几乎一样的笑声，没有任何节奏气息变化" — the previous driving
audio repeated ONE 1.22s laugh clip 4x, and H3 re-rendered it faithfully
(samey output). The v1 MiniMax take's laugh track (native_B.wav) is a real
varied performance: burst1 (turn-laugh) / burst2 (struggle squeal) /
tail (fading giggles).

Strategy:
  driving audio = L07@0.3 + native_B[2.3:7.25] (the whole laugh performance)
  final mix     = L07 clean TTS + THE SAME native_B[2.3:7.25] itself
  (not H3's re-render). The regen video is choreographed to this exact
  rhythm, so the original laughter overlays with zero desync.

Outputs: audio/segB_perf6.wav (driving), audio/bed_B_orig.wav (mix layer)
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUD = ROOT / "output" / "creative_v2" / "couple30_v1" / "audio"


def main() -> int:
    l07 = AUD / "_tmp_perf2" / "L07.wav"
    nb = AUD / "native_B.wav"

    # ---- driving track: L07@0.3 + original laugh performance from 2.3s
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error",
         "-i", str(l07), "-i", str(nb), "-i", str(nb),
         "-filter_complex",
         "[0:a]aresample=44100,pan=stereo|c0=c0|c1=c0,volume=14dB,"
         "adelay=300:all=1,"
         "apad=whole_dur=8.000,atrim=0:8.000[a];"
         "[1:a]atrim=2.30:7.25,asetpts=PTS-STARTPTS,aresample=44100,"
         "pan=stereo|c0=c0|c1=c0,apad=whole_dur=4.950,atrim=0:4.950[n0];"
         "anullsrc=r=44100:cl=stereo:d=2.3[s0];"
         "[s0][n0]concat=n=2:v=0:a=1[n1];"
         "[a][n1]amix=inputs=2:normalize=0,apad=whole_dur=8.000,"
         "atrim=0:8.000[m]",
         "-map", "[m]", "-c:a", "pcm_s16le", str(AUD / "segB_perf6.wav")],
        check=True)
    print("driving perf6 -> L07@0.30 + native_B laugh 2.30-7.25")

    # ---- final-mix layer: original laugh + room tone (silence-first)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error",
         "-i", str(nb), "-i", str(AUD / "bed_B_room.wav"),
         "-filter_complex",
         "[0:a]atrim=2.30:7.25,asetpts=PTS-STARTPTS,aresample=44100,"
         "pan=stereo|c0=c0|c1=c0,volume=-8dB,"
         "apad=whole_dur=4.950,atrim=0:4.950[n0];"
         "anullsrc=r=44100:cl=stereo:d=2.3[s0];"
         "[s0][n0]concat=n=2:v=0:a=1[n1];"
         "[1:a]aresample=44100[r];[n1][r]amix=inputs=2:normalize=0,"
         "apad=whole_dur=8.000,atrim=0:8.000[m]",
         "-map", "[m]", "-c:a", "pcm_s16le", str(AUD / "bed_B_orig.wav")],
        check=True)
    print("mix layer bed_B_orig -> native laugh 2.30-7.25 + room tone")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
