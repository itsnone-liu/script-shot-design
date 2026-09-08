"""Validate story concept candidates before script or shot generation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED = (
    "logline",
    "protagonist_goal",
    "visible_obstacle",
    "product_role",
    "product_causality",
    "action_change",
    "visible_result",
    "beats",
)


def validate(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    candidates = data.get("candidates", [])
    if len(candidates) < 3:
        errors.append("at least three concept candidates are required")
    ids: set[str] = set()
    for c in candidates:
        cid = c.get("id", "<missing-id>")
        if cid in ids:
            errors.append(f"{cid}: duplicate id")
        ids.add(cid)
        for field in REQUIRED:
            if not c.get(field):
                errors.append(f"{cid}: missing {field}")
        if len(c.get("beats", [])) < 4:
            errors.append(f"{cid}: fewer than four story beats")
        if c.get("product_action_limit", 99) > 2:
            errors.append(f"{cid}: product action limit exceeds two")
        scores = c.get("scores", {})
        if scores and not (0 <= scores.get("production_risk", -1) <= 10):
            errors.append(f"{cid}: invalid production risk")
    if not data.get("recommended_order"):
        errors.append("recommended_order is required")
    return errors


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/ad30/concept_candidates.json")
    problems = validate(target)
    if problems:
        print("CONCEPT QA FAILED")
        print("\n".join(f"- {p}" for p in problems))
        raise SystemExit(1)
    print(f"CONCEPT QA PASSED: {target}")
