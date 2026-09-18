# -*- coding: utf-8 -*-
"""couple30 audio timeline: place 11 TTS lines onto segment timelines, build tracks.

Outputs (output/creative_v2/couple30_v1/audio/):
  segA_dialogue.wav  14s — full A dialogue track (drives 乙 regeneration + final mix)
  segB_dialogue.wav   7s
  segC_dialogue.wav  13s
  timeline.json      — actual placement of every line (for mix/lipsync/QA)

Placement: line starts at window start (nudged +0.2s for reaction beat), no overlap,
small bleed allowed past window end (logged). Track length = segment duration.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "output" / "creative_v2" / "couple30_v1" / "audio"
DIA = ROOT / "examples" / "couple30_v1" / "dialogue.json"

SEG_DUR = {"A": 15.0, "B": 7.0, "C": 13.0}  # A uses H3 15s cap (6 dialogue turns)
LEAD = 0.15          # reaction beat before each line
GAP = 0.15           # min gap between lines
SR = 44100


def wav_seconds(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return round(float(r.stdout.strip()), 3)


TRIM = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,"
        "areverse,"
        "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,"
        "areverse")


def trimmed_dur(path: Path) -> float:
    """Measure head/tail-trimmed duration of a line wav."""
    out = path.with_suffix(".trim.wav")
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(path),
                        "-af", TRIM, str(out)])
    if r.returncode:
        return wav_seconds(path)
    d = wav_seconds(out)
    out.unlink(missing_ok=True)
    return d


def build_track(lines: list[dict], dur: float, dest: Path) -> list[dict]:
    """Place lines sequentially at window starts; ffmpeg amix with adelay."""
    placed = []
    cursor = 0.0
    for ln in lines:
        td = trimmed_dur(AUDIO / f"{ln['id']}.wav")
        start = max(ln["window"][0] + LEAD, cursor + GAP)
        placed.append({"id": ln["id"], "speaker": ln["speaker"], "text": ln["text"],
                       "start": round(start, 3), "dur": round(td, 3)})
        cursor = start + td
    if cursor > dur:
        print(f"  WARN: dialogue overruns segment ({cursor:.2f}s > {dur:.2f}s)")
    # ffmpeg: silent base + delayed line mixes (head/tail silence trimmed per line)
    inputs = ["-f", "lavfi", "-t", f"{dur}", "-i", f"anullsrc=r={SR}:cl=stereo"]
    filters = []
    for i, p in enumerate(placed):
        inputs += ["-i", str(AUDIO / f"{p['id']}.wav")]
        ms = int(p["start"] * 1000)
        filters.append(f"[{i+1}:a]{TRIM},aresample={SR},pan=stereo|c0=c0|c1=c1,adelay={ms}|{ms}[d{i}]")
    mix_in = "".join(f"[d{i}]" for i in range(len(placed)))
    filters.append(f"{mix_in}amix=inputs={len(placed)}:normalize=0,apad=whole_dur={dur}[out]")
    cmd = ["ffmpeg", "-y", "-v", "error", *inputs,
           "-filter_complex", ";".join(filters), "-map", "[out]",
           "-c:a", "pcm_s16le", str(dest)]
    r = subprocess.run(cmd)
    if r.returncode:
        raise RuntimeError(f"track build failed {dest}")
    return placed


def main() -> int:
    dia = json.loads(DIA.read_text(encoding="utf-8"))
    lines = dia["lines"]
    missing = [ln["id"] for ln in lines if not (AUDIO / f"{ln['id']}.wav").exists()]
    if missing:
        raise SystemExit(f"missing TTS wavs: {missing}")
    timeline = {}
    for seg, dur in SEG_DUR.items():
        seg_lines = [ln for ln in lines if ln["segment"] == seg]
        dest = AUDIO / f"seg{seg}_dialogue.wav"
        if dest.exists():
            print(f"seg{seg}: exists {dest.name}")
            tl = json.loads((AUDIO / f"seg{seg}_timeline.json").read_text(encoding="utf-8"))
            timeline[seg] = tl
            continue
        placed = build_track(seg_lines, dur, dest)
        (AUDIO / f"seg{seg}_timeline.json").write_text(
            json.dumps(placed, ensure_ascii=False, indent=1), encoding="utf-8")
        timeline[seg] = placed
        print(f"seg{seg} -> {dest.name}")
        for p in placed:
            print(f"   {p['start']:>6.2f}s  {p['speaker']}  {p['text'][:22]}")
    (AUDIO / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    print("saved ->", AUDIO / "timeline.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
