"""Extract explicit C1 contact sheets and technical metadata for visual QA.

This uses one ffmpeg input per requested timestamp and xstack, avoiding the old
f%02d ordering/black-frame failure mode. It never judges images by itself.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "creative_v2" / "coffee30_dont_wake_her_v1"
TIMES = {
    "A": [0.2, 1.4, 2.5, 3.4, 4.5, 5.8, 7.6, 8.8, 10.6, 12.5, 14.7],
    "B": [0.2, 1.5, 2.8, 4.0, 6.3, 7.5, 9.2, 10.5, 12.3, 13.5, 14.8],
}


def probe(path: Path) -> dict:
    raw = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,nb_frames:format=duration",
        "-of", "json", str(path),
    ], text=True)
    return json.loads(raw)


def contact_sheet(path: Path, segment: str, take: int) -> Path:
    qa = OUT / "qa" / f"{segment}_T{take}"
    frames = qa / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    extracted = []
    for index, timestamp in enumerate(TIMES[segment]):
        target = frames / f"f{index:02d}_{timestamp:04.1f}.jpg"
        result = subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-ss", str(timestamp), "-i", str(path),
            "-frames:v", "1", "-vf", "scale=480:-2", str(target),
        ])
        if result.returncode or not target.exists():
            raise RuntimeError(f"frame extraction failed at {timestamp}s")
        extracted.append(target)
    inputs = []
    for frame in extracted:
        inputs.extend(["-i", str(frame)])
    cols = 4
    layout = "|".join(f"{(i%cols)*480}_{(i//cols)*280}" for i in range(len(extracted)))
    chains = ";".join(f"[{i}:v]scale=480:270[v{i}]" for i in range(len(extracted)))
    stack_inputs = "".join(f"[v{i}]" for i in range(len(extracted)))
    sheet = qa / "contact_sheet.jpg"
    filter_complex = f"{chains};{stack_inputs}xstack=inputs={len(extracted)}:layout={layout}:fill=black[out]"
    result = subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", filter_complex, "-map", "[out]", "-frames:v", "1", str(sheet)])
    if result.returncode:
        raise RuntimeError("contact sheet xstack failed")
    (qa / "technical.json").write_text(json.dumps(probe(path), ensure_ascii=False, indent=2), encoding="utf-8")
    return sheet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("--segment", choices=("A", "B"), required=True)
    parser.add_argument("--take", type=int, required=True)
    args = parser.parse_args()
    if not args.video.exists():
        print("missing video", args.video)
        return 2
    print(contact_sheet(args.video, args.segment, args.take))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
