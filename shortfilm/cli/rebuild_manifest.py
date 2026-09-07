"""Rebuild an asset manifest from downloaded raw/vertical shot files."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from shortfilm.cli.validate_project import load


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: python -m shortfilm.cli.rebuild_manifest PROJECT.json OUTPUT_DIR")
        return 2
    project = load(Path(sys.argv[1]))
    output = Path(sys.argv[2])
    shots_dir = output / "shots"
    results = []
    for shot in project.shots:
        raw = shots_dir / f"{shot.shot_id}_00.mp4"
        vertical = shots_dir / f"{shot.shot_id}_00_vertical.mp4"
        if vertical.exists() and vertical.stat().st_size > 0:
            results.append({"shot_id": shot.shot_id, "status": "success",
                            "outputs": [str(vertical)],
                            "raw_outputs": [str(raw)] if raw.exists() else [],
                            "delivery_aspect_ratio": "9:16",
                            "recovered_from_files": True})
        else:
            results.append({"shot_id": shot.shot_id, "status": "missing", "outputs": []})
    manifest = {"project_id": project.project_id, "workflow": "t2v",
                "sequential": True, "results": results}
    output.mkdir(parents=True, exist_ok=True)
    (output / "asset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"rebuilt manifest: {sum(r['status'] == 'success' for r in results)}/{len(results)} shots")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

