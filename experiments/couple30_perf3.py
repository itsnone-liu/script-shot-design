# -*- coding: utf-8 -*-
"""couple30 v2.4 performance tracks — script-logic fix per user:

User: the L07/L08 dialogue happened DURING the turn where the woman is
laughing — that dialogue shouldn't exist there. Redesign:
  B: L07 moves to the very start (he grabs her and says it), then a WORDLESS
     playful tumble with her LAUGHTER (matching the original take's sound
     design: whisper heard no speech, only laughter/struggle).
  C: L08 ("你根本就是装的！") opens C — she calls out his faking right before
     his confession L09 ("从你提 brunch 那句开始…"), which is better drama.
  L09/L10/L11 keep their order, re-spaced after the inserted L08.

Outputs: audio/segB_perf3.wav, audio/segC_perf.wav, audio/timeline_v24.json
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUD = ROOT / "output" / "creative_v2" / "couple30_v1" / "audio"


def run(*cmd: str) -> None:
    subprocess.run(list(cmd), check=True)


def dur(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def stereo_delay(src: Path, at_ms: int) -> str:
    return (f"[{src.stem}_{at_ms}]aresample=44100,"
            f"pan=stereo|c0=c0|c1=c0,adelay={at_ms}|{at_ms}")


def build(name: str, items: list[tuple[Path, int]], total: float,
          extra_filters: dict[int, str] | None = None) -> Path:
    """items: (wav, at_ms). Returns mixed wav padded/trimmed to total."""
    dest = AUD / name
    cmd = ["ffmpeg", "-y", "-v", "error"]
    inputs = []
    for src, at in items:
        cmd += ["-i", str(src)]
        inputs.append((src, at, len(inputs)))
    parts = []
    for src, at, idx in inputs:
        pre = f"[{idx}:a]"
        if extra_filters and at in extra_filters:
            pre += extra_filters[at]
        parts.append(f"{pre}aresample=44100,pan=stereo|c0=c0|c1=c0,"
                     f"adelay={at}|{at}[d{idx}]")
    mix_in = "".join(f"[d{i}]" for _, _, i in inputs)
    vf = ";".join(parts) + f";{mix_in}amix=inputs={len(inputs)}:normalize=0," \
          f"apad=whole_dur={total:.3f},atrim=0:{total:.3f}[m]"
    run(*cmd, "-filter_complex", vf, "-map", "[m]", "-c:a", "pcm_s16le",
        str(dest))
    return dest


def trim_sil(p: Path, dest: Path) -> Path:
    run("ffmpeg", "-y", "-v", "error", "-i", str(p), "-af",
        "silenceremove=start_periods=1:start_threshold=-45dB,"
        "areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse",
        "-c:a", "pcm_s16le", str(dest))
    return dest


def main() -> int:
    l07 = AUD / "_tmp_perf2" / "L07.wav"   # lite render 1.68s
    l08 = AUD / "_tmp_perf2" / "L08.wav"   # lite render 0.98s
    tmp = AUD / "_tmp_perf2"
    l09 = trim_sil(AUD / "L09.wav", tmp / "L09_t.wav")
    l10 = trim_sil(AUD / "L10.wav", tmp / "L10_t.wav")
    l11 = trim_sil(AUD / "L11.wav", tmp / "L11_t.wav")
    laugh = AUD / "laugh_B.wav"
    for p in (l07, l08, l09, l10, l11, laugh):
        print(p.name, round(dur(p), 2), "s")

    # --- B: L07 at 0.30s (grab moment), laughter at 5.60s (she nuzzles-laughs)
    b_total = 8.0
    build("segB_perf3.wav", [(l07, 300), (laugh, 5600)], b_total,
          extra_filters={5600: "volume=-6dB,"})
    tl_b = [{"id": "L07", "start": 0.30, "dur": round(dur(l07), 2)}]

    # --- C: L08 0.40 / L09 1.90 / L10 re-space / L11 re-space
    d09, d10, d11 = dur(l09), dur(l10), dur(l11)
    t08, t09 = 0.40, 1.90
    t10 = t09 + d09 + 0.35
    t11 = t10 + d10 + 0.30
    c_total = 13.7
    assert t11 + d11 <= c_total, "C overflow"
    build("segC_perf.wav",
          [(l08, int(t08 * 1000)), (l09, int(t09 * 1000)),
           (l10, int(t10 * 1000)), (l11, int(t11 * 1000))], c_total)
    tl_c = [{"id": "L08", "start": round(t08, 2), "dur": round(dur(l08), 2)},
            {"id": "L09", "start": round(t09, 2), "dur": round(d09, 2)},
            {"id": "L10", "start": round(t10, 2), "dur": round(d10, 2)},
            {"id": "L11", "start": round(t11, 2), "dur": round(d11, 2)}]

    tl = json.loads((AUD / "timeline.json").read_text(encoding="utf-8-sig"))
    tl_v24 = {"A": tl["A"], "B": tl_b, "C": tl_c}
    (AUD / "timeline_v24.json").write_text(
        json.dumps(tl_v24, ensure_ascii=False, indent=1), encoding="utf-8")
    print("B perf3 -> 8.0s (L07@0.30 + laugh@5.60)")
    print(f"C perf -> 13.7s (L08@{t08:.2f} L09@{t09:.2f} "
          f"L10@{t10:.2f} L11@{t11:.2f})")
    print("timeline_v24.json written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
