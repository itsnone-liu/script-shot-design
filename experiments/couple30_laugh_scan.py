# -*- coding: utf-8 -*-
"""Scan native B audio for laughter bursts (1.5-5kHz energy outside dialogue)."""
import subprocess

WAV = r"output\creative_v2\couple30_v1\audio\native_B.wav"
DIALOGUE = [(1.65, 4.15), (4.15, 6.15)]


def band_db(t0: float, t1: float, lo=1500, hi=5000) -> float | None:
    r = subprocess.run(
        ["ffmpeg", "-v", "info", "-ss", f"{t0:.2f}", "-to", f"{t1:.2f}", "-i", WAV,
         "-af", f"highpass=f={lo},lowpass=f={hi},astats=metadata=0", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    for ln in r.stderr.splitlines():
        if "RMS level dB" in ln:
            try:
                return float(ln.split(":")[-1])
            except ValueError:
                return None
    return None


def main() -> None:
    rows = []
    for i in range(29):
        t0 = i * 0.25
        db = band_db(t0, t0 + 0.25)
        if db is None:
            continue
        ind = any(a <= t0 <= b for a, b in DIALOGUE)
        rows.append((t0, db, "DIALOG" if ind else "FREE"))
        print(f"{t0:6.2f}s {db:7.1f}dB {'DIALOG' if ind else 'FREE'}")
    free = [r for r in rows if r[2] == "FREE" and r[1] > -50]
    if free:
        best = max(free, key=lambda r: r[1])
        print(f"\nstrongest FREE burst: {best[0]:.2f}s {best[1]:.1f}dB")


if __name__ == "__main__":
    main()
