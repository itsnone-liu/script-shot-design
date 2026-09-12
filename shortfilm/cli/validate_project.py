"""Validate a structured ad project: python -m shortfilm.cli.validate_project file.json"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from shortfilm.model import AdProject, Shot


def load(path: Path) -> AdProject:
    raw = json.loads(path.read_text(encoding="utf-8"))
    shots = [Shot(**item) for item in raw.pop("shots", [])]
    allowed = {"project_id", "title", "duration_target", "aspect_ratio", "audience", "product", "core_message", "visual_style", "story_template", "user_script_review"}
    raw = {key: value for key, value in raw.items() if key in allowed}
    return AdProject(shots=shots, **raw)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python -m shortfilm.cli.validate_project PROJECT.json")
        return 2
    project = load(Path(sys.argv[1]))
    errors = project.validate()
    if errors:
        print("INVALID")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"VALID: {project.project_id} ({len(project.shots)} shots, {project.duration_target:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

