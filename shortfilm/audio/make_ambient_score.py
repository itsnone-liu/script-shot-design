"""Create a deterministic 30-second cinematic ambient score with stdlib only."""

from __future__ import annotations

import math
import random
import struct
import sys
import wave
from pathlib import Path

RATE = 48_000
DURATION = 30.4
TAU = math.tau


def smoothstep(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def section_weight(t: float, start: float, end: float, fade: float = 1.8) -> float:
    return smoothstep((t - start) / fade) * smoothstep((end - t) / fade)


def bell(t: float, at: float, freq: float) -> float:
    age = t - at
    if age < 0.0 or age > 5.0:
        return 0.0
    attack = smoothstep(age / 0.025)
    decay = math.exp(-age * 0.72)
    return attack * decay * (
        math.sin(TAU * freq * age)
        + 0.34 * math.sin(TAU * freq * 2.01 * age)
        + 0.13 * math.sin(TAU * freq * 3.97 * age)
    )


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: make_ambient_score.py OUTPUT.wav")
        return 2
    output = Path(sys.argv[1])
    output.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(821)
    noise_state = 0.0
    frames = bytearray()
    peak = 0.0
    rendered: list[tuple[float, float]] = []
    for i in range(round(RATE * DURATION)):
        t = i / RATE
        # Cm(add9) -> Abmaj7 -> Cmaj9: darkness, expansion, resolution.
        w1 = section_weight(t, -1.0, 11.2)
        w2 = section_weight(t, 8.7, 21.5)
        w3 = section_weight(t, 18.5, 31.5)
        pad = 0.0
        for freq, gain in ((65.41, .34), (98.00, .20), (155.56, .13), (293.66, .055)):
            pad += w1 * gain * math.sin(TAU * freq * t + .18 * math.sin(TAU * .07 * t))
        for freq, gain in ((51.91, .25), (103.83, .17), (155.56, .12), (196.00, .07)):
            pad += w2 * gain * math.sin(TAU * freq * t + .14 * math.sin(TAU * .05 * t))
        for freq, gain in ((65.41, .28), (98.00, .17), (164.81, .15), (293.66, .07)):
            pad += w3 * gain * math.sin(TAU * freq * t + .10 * math.sin(TAU * .04 * t))
        pulse = 0.0
        for at in (10.2, 12.7, 15.2, 17.7, 20.2, 22.7, 25.2, 27.7):
            age = t - at
            if 0 <= age < 1.2:
                pulse += math.exp(-age * 4.0) * math.sin(TAU * 130.81 * age) * 0.09
        chime = sum(bell(t, at, freq) for at, freq in ((1.0, 523.25), (9.7, 392.0), (19.8, 659.25), (27.2, 783.99))) * .075
        noise_state = noise_state * .9985 + (rng.random() * 2 - 1) * .0015
        air = noise_state * (0.018 + 0.018 * w2)
        fade_in = smoothstep(t / 1.8)
        fade_out = smoothstep((DURATION - t) / 1.6)
        base = (pad * .34 + pulse + chime + air) * fade_in * fade_out
        width = .018 * math.sin(TAU * .11 * t)
        left = base + width * pad
        right = base - width * pad
        peak = max(peak, abs(left), abs(right))
        rendered.append((left, right))
    scale = 0.82 / max(peak, 1e-9)
    for left, right in rendered:
        frames.extend(struct.pack("<hh", int(left * scale * 32767), int(right * scale * 32767)))
    with wave.open(str(output), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(frames)
    print(f"wrote {output} ({DURATION:.1f}s stereo 48kHz)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
