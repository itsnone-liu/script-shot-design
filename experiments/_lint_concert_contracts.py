# -*- coding: utf-8 -*-
"""Lint the concert contracts with the repo camera lint + contract schema."""
import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shortfilm.camera_lint import lint_camera  # noqa: E402
from shortfilm import prompt_contract as pc  # noqa: E402

for name in ("segA_v1.json", "segB_v1.json"):
    path = ROOT / "examples" / "concert30_hcy_flowers" / name
    doc = json.loads(path.read_text(encoding="utf-8"))
    print(f"==== {name} ====")
    findings = lint_camera(doc)
    if not findings:
        print("  camera_lint: CLEAN")
    for f in findings:
        print(f"  camera_lint: {f}")
    # coverage check
    shots = doc["internal_shots"]
    t = 0.0
    for s in shots:
        gap = round(s["start"] - t, 3)
        flag = "" if abs(gap) < 1e-6 else f"  <-- GAP/OVERLAP {gap}s"
        print(f"  {s['shot_id']}: {s['start']}-{s['end']}{flag}")
        t = s["end"]
    tail = round(doc["duration"] - t, 3)
    print(f"  tail to duration end: {tail}s")
    # schema keys per shot
    required = {"shot_id", "start", "end", "transition_in", "shot_size", "visual_state",
                "subject_action", "camera_action", "focus", "lighting_state", "end_state",
                "camera_plan", "cinematic_design"}
    for s in shots:
        missing = required - set(s.keys())
        if missing:
            print(f"  MISSING KEYS in {s['shot_id']}: {missing}")
    cp = s.get("camera_plan", {})
    cp_required = {"motivation", "start_position", "path", "speed_curve", "focus_transition",
                   "end_position", "axis_lock", "stop_condition", "primary_move", "path_changes"}
    for s in shots:
        missing = cp_required - set(s.get("camera_plan", {}).keys())
        if missing:
            print(f"  MISSING camera_plan keys in {s['shot_id']}: {missing}")
    print("  schema check done")
