# -*- coding: utf-8 -*-
"""Fine envelope analysis of native B bursts: laughter shows 4-8Hz periodic
peaks/valleys; music is sustained. 50ms windows over candidate spans."""
import subprocess

WAV = r"output\creative_v2\couple30_v1\audio\native_B.wav"


def band_db(t0: float, t1: float) -> float | None:
    r = subprocess.run(
        ["ffmpeg", "-v", "info", "-ss", f"{t0:.3f}", "-to", f"{t1:.3f}", "-i", WAV,
         "-af", "highpass=f=1500,lowpass=f=5000,astats=metadata=0", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    for ln in r.stderr.splitlines():
        if "RMS level dB" in ln:
            try:
                return float(ln.split(":")[-1])
            except ValueError:
                return None
    return None


def analyze(t0: float, t1: float, label: str) -> None:
    n = int((t1 - t0) / 0.05)
    dbs = []
    for i in range(n):
        db = band_db(t0 + i * 0.05, t0 + i * 0.05 + 0.05)
        if db is not None:
            dbs.append(db)
    if not dbs:
        return
    hi, lo = max(dbs), min(dbs)
    swings = sum(1 for a, b in zip(dbs, dbs[1:]) if abs(a - b) > 6)
    print(f"{label} {t0}-{t1}s: windows={len(dbs)} max={hi:.1f} min={lo:.1f} "
          f"span={hi-lo:.1f}dB bigSwings(>6dB/50ms)={swings}")
    print("  ", " ".join(f"{d:.0f}" for d in dbs))


if __name__ == "__main__":
    analyze(2.70, 3.85, "burst1")
    analyze(4.70, 6.05, "burst2")
    analyze(6.20, 7.20, "tail")
