"""Normalize RH outputs to the project's delivery frame before editing."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def normalize(src: Path, dst: Path, *, focus: float = 0.38, width: int = 864, height: int = 1536) -> None:
    """Crop a landscape render to 9:16 around a normalized horizontal focus.

    `focus` is the subject's approximate x position (0..1). It is stored per
    shot later; 0.38 keeps the main subject in the S01 sample inside the crop.
    """
    if not 0 <= focus <= 1:
        raise ValueError("focus must be between 0 and 1")
    # Crop to 9:16, preserve the source height, then scale. The x expression
    # keeps the selected subject location rather than blindly center-cropping.
    # `focus` is constrained to [0,1], so this x coordinate is already within
    # the legal crop range and avoids commas that must be escaped in ffmpeg.
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "json", str(src)],
        check=True, capture_output=True, text=True,
    )
    stream = json.loads(probe.stdout)["streams"][0]
    source_ratio = float(stream["width"]) / float(stream["height"])
    target_ratio = width / height
    if source_ratio > target_ratio + 0.001:
        vf = f"crop=ih*{width}/{height}:ih:(iw-ih*{width}/{height})*{focus}:0,scale={width}:{height}:flags=lanczos,setsar=1"
    else:
        vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease:flags=lanczos,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1"
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", "-i", str(src), "-vf", vf, "-map", "0:v:0", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(dst),
    ], check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path)
    ap.add_argument("destination", type=Path)
    ap.add_argument("--focus", type=float, default=0.38)
    args = ap.parse_args()
    normalize(args.source, args.destination, focus=args.focus)
    print(f"normalized {args.source} -> {args.destination} (9:16)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
