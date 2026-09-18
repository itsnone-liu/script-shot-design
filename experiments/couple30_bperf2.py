# -*- coding: utf-8 -*-
"""couple30 v2.3: B performance track v2 — effortful delivery.

User note: during the tumble (B 1.9-4.9s abs) the dialogue sounds too calm.
Fix without breaking lip timing (same words, same placements):
  - re-render L07/L08 with faster rate + slight pitch up (exerted voice)
  - layer native struggle sounds (burst2 4.70-6.05s, band-passed so it reads
    as effort/breathing, not speech) underneath the lines
  - keep the placed laughter at 6.15s
Output: audio/segB_perf2.wav (~7.4s)
"""
from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUD = ROOT / "output" / "creative_v2" / "couple30_v1" / "audio"

L07 = {"id": "L07", "text": "再睡五分钟——这回你陪我。",
       "voice": "zh-CN-YunxiNeural", "rate": "+12%", "pitch": "+8Hz",
       "at_ms": 1650}
L08 = {"id": "L08", "text": "你根本就是装的！",
       "voice": "zh-CN-XiaoyiNeural", "rate": "+15%", "pitch": "+12Hz",
       "at_ms": 4150}


async def tts(line: dict, dest: Path) -> None:
    import edge_tts
    c = edge_tts.Communicate(line["text"], line["voice"], rate=line["rate"],
                             pitch=line["pitch"])
    await c.save(str(dest))


def run(*cmd: str) -> None:
    subprocess.run(list(cmd), check=True)


def trim(in_w: Path, out_w: Path) -> None:
    run("ffmpeg", "-y", "-v", "error", "-i", str(in_w), "-af",
        "silenceremove=start_periods=1:start_threshold=-45dB,"
        "areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse",
        "-c:a", "pcm_s16le", str(out_w))


def main() -> int:
    raw = AUD / "_tmp_perf2"
    raw.mkdir(exist_ok=True)
    for ln in (L07, L08):
        asyncio.run(tts(ln, raw / f"{ln['id']}_raw.mp3"))
        trim(raw / f"{ln['id']}_raw.mp3", raw / f"{ln['id']}.wav")
        d = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration", "-of", "csv=p=0",
                            str(raw / f"{ln['id']}.wav")],
                           capture_output=True, text=True).stdout.strip()
        print(f"{ln['id']} trimmed dur {d}s (placed at {ln['at_ms']}ms)")

    # struggle SFX: native burst2, band-passed to effort/breath character
    sfx = raw / "sfx.wav"
    run("ffmpeg", "-y", "-v", "error", "-ss", "4.70", "-to", "6.05",
        "-i", str(AUD / "native_B.wav"), "-af",
        "highpass=f=280,lowpass=f=3200,volume=-11dB,"
        "afade=t=in:d=0.10,afade=t=out:st=1.15:d=0.20,"
        "aresample=44100,pan=stereo|c0=c0|c1=c0", "-c:a", "pcm_s16le", str(sfx))

    # effort loop under both lines: 2.0-4.2 and 4.35-6.05
    perf = AUD / "segB_perf2.wav"
    run("ffmpeg", "-y", "-v", "error",
        "-i", str(raw / "L07.wav"), "-i", str(raw / "L08.wav"),
        "-i", str(sfx), "-i", str(AUD / "laugh_B.wav"),
        "-filter_complex",
        "[0:a]aresample=44100,pan=stereo|c0=c0|c1=c0,adelay=1650|1650[a];"
        "[1:a]aresample=44100,pan=stereo|c0=c0|c1=c0,adelay=4150|4150[b];"
        "[2:a]adelay=2000|2000[s1];[2:a]adelay=4350|4350[s2];"
        "[3:a]volume=-6dB,adelay=6150|6150[g];"
        "[a][b][s1][s2][g]amix=inputs=5:normalize=0,"
        "apad=whole_dur=7.400,atrim=0:7.400[m]",
        "-map", "[m]", "-c:a", "pcm_s16le", str(perf))
    print("perf2 ->", perf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
