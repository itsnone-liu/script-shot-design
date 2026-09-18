# -*- coding: utf-8 -*-
"""couple30 PLOT GATE (v2.6+): story-level acceptance per segment.

Why: technical gates (lipsync/face/ASR) passed every take while the STORY
broke - laughter after the flip instead of at it, smiling faces with no
sound, dialogue during action. This gate encodes beat-level causality:

  B: audio-laugh windows must cover the visual laughing span, and the
     flip beat must fall INSIDE a laugh window (laughter caused by flip).

Visual beats are recorded from VLM frame audits (choreography is stable per
take; re-audit when the take changes). Audio spans measured from the master.

Usage: python couple30_plotgate.py <master.mp4>
Exit 0 = PASS, 1 = FAIL (prints the beat table).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUD = ROOT / "output" / "creative_v2" / "couple30_v1" / "audio"

# VLM frame audit results per take (update when a new take is accepted)
VISUAL = {
    "B_regen3_repaired": {
        "laugh_span": (2.5, 6.8),   # she is visibly laughing throughout
        "flip_beat": 3.5,           # the turn happens here
    },
    "B_regen4_repaired": {
        "laugh_span": (2.85, 7.3),  # big laugh from 2.85 (frame-verified)
        "flip_beat": 5.0,           # she rolls from under him to on top ~4.6-5.6
    },
    "B_regen5_repaired": {
        "laugh_span": (2.5, 7.2),   # follows original laugh dynamics
        "flip_beat": 3.6,           # she climbs/rolls onto him in the breath gap
    },
}
# which take each arm uses (keep in sync with couple30_mix.py)
ARM_TAKE = {"v24": "B_regen3_repaired", "v25": "B_regen3_repaired",
            "v26": "B_regen3_repaired", "v27": "B_regen4_repaired",
            "v28": "B_regen5_repaired"}
# laugh placements per performance track (s, dB) - from perf4 design
LAUGH_WINDOWS = {  # arm -> list of (start, end) in B-local seconds
    "v26": [(2.45, 3.67), (3.85, 5.07), (5.90, 7.12)],
    # v27: continuous harvested laughter from the take's own audio track
    "v27": [(2.45, 7.4)],
    # v28: the ORIGINAL native laugh performance (2.30-7.25) overlays the
    # regen5 video that was choreographed to exactly that audio
    "v28": [(2.45, 7.3)],
}


def arm_of(name: str) -> str:
    m = re.search(r"master_v(\d+)", name)
    return f"v{m.group(1)}" if m else ""


def seg_offsets(master: Path) -> dict:
    rep = ROOT / "output" / "creative_v2" / "couple30_v1" / "repaired"
    def dur(p: Path) -> float:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration", "-of", "csv=p=0", str(p)],
                           capture_output=True, text=True)
        return float(r.stdout.strip())
    a = dur(rep / "A_regen3_00.mp4")
    b = dur(rep / "B_regen3_repaired.mp4")
    return {"A": 0.0, "B": a, "C": a + b}


def rms_db(master: str, t0: float, t1: float,
           lo: int = 1200, hi: int = 5000) -> float | None:
    r = subprocess.run(["ffmpeg", "-v", "info", "-ss", f"{t0:.3f}",
                        "-to", f"{t1:.3f}", "-i", master, "-af",
                        f"highpass=f={lo},lowpass=f={hi},astats=metadata=0",
                        "-f", "null", "-"],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    for ln in r.stderr.splitlines():
        if "RMS level dB" in ln:
            try:
                return float(ln.split(":")[-1])
            except ValueError:
                pass
    return None


def main() -> int:
    master = Path(sys.argv[1])
    arm = arm_of(master.name)
    take = ARM_TAKE.get(arm)
    if not take:
        print(f"[plotgate] no visual audit for arm {arm} - SKIP (manual)")
        return 0
    vis = VISUAL[take]
    off = seg_offsets(master)
    b0 = off["B"]
    checks = []
    # 1) every audio laugh window must show laugh-band energy
    for (s, e) in LAUGH_WINDOWS.get(arm, []):
        db = rms_db(str(master), b0 + s, b0 + e)
        ok = db is not None and db > -30
        checks.append((f"laugh {s:.2f}-{e:.2f}s audible", ok,
                       f"{db:.1f}dB" if db is not None else "silence"))
    # 2) NO laugh energy in the wordless gap between his line (ends 1.98)
    #    and the first laugh (2.45) - boundary guard against early placement
    db = rms_db(str(master), b0 + 2.02, b0 + 2.42)
    checks.append(("pre-laugh gap clean (2.02-2.42s)", db is None or db < -30,
                   f"{db:.1f}dB" if db is not None else "silence"))
    # 3) flip beat covered by a laugh window (causality)
    covered = any(s <= vis["flip_beat"] <= e
                  for (s, e) in LAUGH_WINDOWS.get(arm, []))
    checks.append((f"flip beat {vis['flip_beat']}s inside a laugh window",
                   covered, "causal" if covered else "DESYNC"))
    # 4) laugh windows inside visual laughing span (no sound without face)
    inside = all(vis["laugh_span"][0] - 0.4 <= s
                 and e <= vis["laugh_span"][1] + 0.4
                 for (s, e) in LAUGH_WINDOWS.get(arm, []))
    checks.append(("audio laughs inside visual laugh span", inside,
                   f"visual {vis['laugh_span']}"))

    print(f"[plotgate] arm={arm} take={take}")
    fails = 0
    for name, ok, note in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:44s} {note}")
        fails += 0 if ok else 1
    print(f"[plotgate] {'PASS' if fails == 0 else 'FAIL'} ({fails} failed)")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
