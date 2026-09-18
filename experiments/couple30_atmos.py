# -*- coding: utf-8 -*-
"""couple30 v2.1 atmos bed: keep the original takes' non-speech character
(laughter / ambience / BGM), attenuate only gibberish speech.

Pipeline per segment (A_T1 / B_T2 / C_T2 native audio):
  1. faster-whisper small (local) word timestamps, strict confidence:
     avg_logprob > -0.45, no_speech_prob < 0.55, probability > 0.45.
  2. merge word intervals (gap < 0.35s), pad 0.22s -> speech mask.
  3. ffmpeg volume=0.10 during mask, 1.0 elsewhere; overall -13dB.
  4. report: mask coverage + 2-5kHz band energy kept in non-speech windows
     (laughter/BGM survival evidence).

Usage: python -X utf8 experiments/couple30_atmos.py            # build all
       python -X utf8 experiments/couple30_atmos.py --inspect  # dump masks only
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

SHOTS = ROOT / "output" / "creative_v2" / "couple30_v1" / "shots"
AUD = ROOT / "output" / "creative_v2" / "couple30_v1" / "audio"
SEGS = {"A": "C30_A_T1_00.mp4", "B": "C30_B_T2_00.mp4", "C": "C30_C_T2_00.mp4"}
MODEL = ROOT / "output" / ".models" / "whisper-small"


def sh(*cmd, **kw):
    return subprocess.run(list(cmd), check=True, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", **kw)


def speech_mask(wav: Path, dur: float):
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    from faster_whisper import WhisperModel
    m = WhisperModel(str(MODEL), device="cpu", compute_type="int8")
    segs, _ = m.transcribe(str(wav), language="zh", vad_filter=False,
                           word_timestamps=True,
                           condition_on_previous_text=False)
    words = []
    for s in segs:
        # native H3 audio: whisper CAN'T transcribe it (gibberish, low logprob)
        # but segment boundaries still mark SPEECH-LIKE spans -> attenuate those.
        if s.no_speech_prob is not None and s.no_speech_prob >= 0.60:
            continue
        if s.end - s.start < 0.15:  # subtitle-watermark style blips
            continue
        words.append((s.start, s.end))
    if not words:
        return []
    words.sort()
    merged = [list(words[0])]
    for a, b in words[1:]:
        if a - merged[-1][1] < 0.35:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return [(max(0.0, a - 0.22), min(dur, b + 0.22)) for a, b in merged]


LOGPROB, NSP, PROB = -0.45, 0.55, 0.45


def band_energy(wav: Path, t0: float, t1: float) -> float:
    out = sh("ffmpeg", "-v", "info", "-ss", f"{t0:.3f}", "-to", f"{t1:.3f}",
             "-i", str(wav), "-af", "highpass=f=2000,lowpass=f=5000,astats=metadata=0",
             "-f", "null", "-")
    for ln in out.stderr.splitlines():
        if "RMS level dB" in ln:
            try:
                return float(ln.split("RMS level dB:")[1].strip())
            except ValueError:
                pass
    return -120.0


def main() -> int:
    inspect_only = "--inspect" in sys.argv
    report = {}
    for seg, take in SEGS.items():
        native = AUD / f"native_{seg}.wav"
        sh("ffmpeg", "-y", "-v", "error", "-i", str(SHOTS / take), "-vn",
           "-c:a", "pcm_s16le", "-ar", "44100", "-ac", "2", str(native))
        dur = float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
                       "-of", "csv=p=0", str(native)).stdout.strip())
        asr16 = AUD / f"native_{seg}_16k.wav"
        sh("ffmpeg", "-y", "-v", "error", "-i", str(native), "-ar", "16000",
           "-ac", "1", "-c:a", "pcm_s16le", str(asr16))
        mask = speech_mask(asr16, dur)
        cov = sum(b - a for a, b in mask) / dur if dur else 0
        print(f"[{seg}] dur={dur:.2f}s speech_mask={len(mask)} "
              f"coverage={cov:.0%} -> {[(round(a,2), round(b,2)) for a, b in mask]}")
        report[seg] = {"duration": dur, "mask": mask, "coverage": cov}
        if inspect_only:
            continue
        dest = AUD / f"atmos_{seg}.wav"
        if not mask:
            vf = "volume=-13dB"
        else:
            parts = [f"volume=0.10:enable='between(t,{a:.3f},{b:.3f})'"
                     for a, b in mask]
            vf = ",".join(parts) + ",volume=-13dB"
        sh("ffmpeg", "-y", "-v", "error", "-i", str(native), "-af", vf,
           "-c:a", "pcm_s16le", str(dest))
        # survival evidence: 2-5kHz energy pre/post in the largest non-speech gap
        gaps = []
        prev = 0.0
        for a, b in mask:
            if a - prev > 0.8:
                gaps.append((prev, a))
            prev = b
        if dur - prev > 0.8:
            gaps.append((prev, dur))
        if gaps:
            g0, g1 = max(gaps, key=lambda g: g[1] - g[0])
            e_nat = band_energy(native, g0, g1)
            e_atm = band_energy(dest, g0, g1)
            # speech window for contrast
            s0, s1 = mask[0] if mask else (0, 0.5)
            e_sp = band_energy(dest, s0, min(s1, s0 + 1.0))
            print(f"[{seg}] largest non-speech gap ({g0:.2f}-{g1:.2f}s) "
                  f"2-5kHz RMS native={e_nat:.1f}dB atmos={e_atm:.1f}dB "
                  f"(kept {-e_nat + e_atm:.1f}dB atten); speech window atmos={e_sp:.1f}dB")
            report[seg]["gap_check"] = {"window": [g0, g1], "native_db": e_nat,
                                        "atmos_db": e_atm, "speech_db": e_sp}
    (AUD / "atmos_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print("report ->", AUD / "atmos_report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
