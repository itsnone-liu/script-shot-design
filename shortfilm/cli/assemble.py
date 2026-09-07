"""Assemble the normalized shot videos according to the planned durations."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from shortfilm.cli.validate_project import load


def assemble(project_path: Path, shots_dir: Path, destination: Path) -> None:
    project = load(project_path)
    inputs = []
    filters = []
    for index, shot in enumerate(project.shots):
        path = shots_dir / f"{shot.shot_id}_00_vertical.mp4"
        if not path.exists():
            raise FileNotFoundError(path)
        inputs += ["-i", str(path)]
        duration = f"{shot.duration:.3f}"
        filters.append(f"[{index}:v]trim=duration={duration},setpts=PTS-STARTPTS[v{index}]")
    concat_inputs = "".join(f"[v{i}]" for i in range(len(project.shots)))
    filters.append(f"{concat_inputs}concat=n={len(project.shots)}:v=1:a=0[outv]")
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters),
        "-map", "[outv]", "-an", "-r", "24",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(destination),
    ], check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", type=Path)
    ap.add_argument("shots_dir", type=Path)
    ap.add_argument("destination", type=Path)
    args = ap.parse_args()
    assemble(args.project, args.shots_dir, args.destination)
    print(f"assembled {args.destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
