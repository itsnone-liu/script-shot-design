"""Render an ad's shots sequentially through 820/RunningHub.

Use --dry-run first. Without it, tasks are submitted one at a time and each task
is fully polled before the next shot starts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from shortfilm.cli.build_packets import main as build_packets_main
from shortfilm.cli.validate_project import load
from shortfilm.rh_adapter import render_packet
from shortfilm import rh_adapter
from shortfilm.cli.normalize_video import normalize
from shortfilm.knowledge.runtime import get_card


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--workflow", choices=("t2v", "i2v"), default="t2v")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--poll", type=float, default=10.0)
    ap.add_argument("--max-wait", type=float, default=1200.0)
    ap.add_argument("--reference-image", type=Path, default=None,
                    help="character/product reference image; uploaded once and reused")
    ap.add_argument("--reference-map", type=Path, default=None,
                    help="JSON object mapping shot_id to local image path")
    args = ap.parse_args()
    project = load(args.project)
    card = get_card()
    errors = project.validate()
    if errors:
        print("INVALID PROJECT")
        print("\n".join(f"- {e}" for e in errors))
        return 1
    packet_dir = args.output / "packets"
    packet_dir.mkdir(parents=True, exist_ok=True)
    reference_paths: dict[str, Path] = {}
    end_reference_paths: dict[str, Path] = {}
    if args.reference_map:
        try:
            raw_map = json.loads(args.reference_map.read_text(encoding="utf-8"))
            if not isinstance(raw_map, dict):
                raise ValueError("top-level value must be an object")
            for shot_id, raw_path in raw_map.items():
                end_raw = None
                if isinstance(raw_path, dict):
                    end_raw = raw_path.get("last")
                    raw_path = raw_path.get("first")
                if not raw_path:
                    raise ValueError(f"{shot_id}: first image is required")
                path = Path(str(raw_path))
                if not path.is_absolute():
                    path = args.reference_map.parent / path
                reference_paths[str(shot_id)] = path.resolve()
                if end_raw:
                    end_path = Path(str(end_raw))
                    if not end_path.is_absolute():
                        end_path = args.reference_map.parent / end_path
                    end_reference_paths[str(shot_id)] = end_path.resolve()
        except (OSError, ValueError, TypeError) as exc:
            print(f"invalid reference map: {exc}")
            return 1

    candidates = list(reference_paths.values()) + list(end_reference_paths.values())
    if args.reference_image:
        candidates.append(args.reference_image.resolve())
    missing = sorted({str(path) for path in candidates if not path.is_file()})
    if missing:
        print("missing reference image(s):")
        print("\n".join(f"- {path}" for path in missing))
        return 1

    upload_cache: dict[str, str] = {}
    rh_key = None

    def upload_reference(path: Path | None) -> str:
        nonlocal rh_key
        if path is None:
            return ""
        cache_key = str(path)
        if args.dry_run:
            return f"<upload:{cache_key}>"
        if cache_key not in upload_cache:
            if rh_key is None:
                rh_key = rh_adapter.rh_task.load_api_key()
            if not rh_key:
                raise RuntimeError("reference image requested but RH API key unavailable")
            upload_cache[cache_key] = rh_adapter.rh_task.upload_file(rh_key, path)
            print(f"reference uploaded once: {path.name}")
        return upload_cache[cache_key]

    def reference_for(shot_id: str) -> str:
        path = reference_paths.get(shot_id)
        if path is None and args.reference_image:
            path = args.reference_image.resolve()
        return upload_reference(path)

    def end_reference_for(shot_id: str) -> str:
        return upload_reference(end_reference_paths.get(shot_id))
    raw_packets = []
    for shot in project.shots:
        # Screen/UI composites are produced in post and must not consume RH jobs.
        if shot.generation_workflow != "rh_video":
            continue
        prompt_parts = [shot.generation_prompt] if shot.generation_prompt else [
            project.visual_style,
            card["prompt_constraints"]["positive"],
            shot.subject_action, shot.lighting, shot.composition,
            f"single attention subject: {shot.attention_subject}, product visibility: {shot.product_visibility}",
            f"{shot.shot_size}, {shot.angle}, camera {shot.camera_move}",
            f"movement intent {shot.movement_intent}, {shot.movement_speed} speed",
            f"start {shot.start_framing}, end {shot.end_framing}",
            f"screen direction {shot.screen_direction}, {shot.stabilization} stabilization",
            "preserve identity and continuity, no text or logo",
            "avoid: " + card["prompt_constraints"]["negative"],
        ]
        raw_packets.append({"shot_id": shot.shot_id, "duration": shot.duration,
                            "prompt": "; ".join(filter(None, prompt_parts))})
    end = len(raw_packets) if not args.limit else min(len(raw_packets), args.start + args.limit)
    manifest_path = args.output / "asset_manifest.json"
    results = []
    if manifest_path.exists():
        try:
            previous = json.loads(manifest_path.read_text(encoding="utf-8"))
            results.extend(previous.get("results") or [])
        except (OSError, ValueError):
            pass
    previous_by_shot = {item.get("shot_id"): item for item in results}
    completed_this_run = 0
    for packet in raw_packets[args.start:end]:
        print(f"\n=== {packet['shot_id']} ({packet['duration']}s) ===")
        existing = previous_by_shot.get(packet["shot_id"])
        if existing and existing.get("status") == "success":
            existing_outputs = [Path(path) for path in existing.get("outputs") or []]
            if existing_outputs and all(path.is_file() for path in existing_outputs):
                print("resume: existing successful output retained")
                continue
        recovered = args.output / "shots" / f"{packet['shot_id']}_00_vertical.mp4"
        if not args.dry_run and recovered.is_file():
            previous_by_shot[packet["shot_id"]] = {
                "shot_id": packet["shot_id"], "status": "success",
                "outputs": [str(recovered)], "recovered": True,
                "delivery_aspect_ratio": "9:16",
            }
            print("resume: recovered normalized output from disk")
            recovered_manifest = {
                "project_id": project.project_id, "workflow": args.workflow,
                "sequential": True, "completed_in_this_run": completed_this_run,
                "results": list(previous_by_shot.values()),
            }
            manifest_path.write_text(
                json.dumps(recovered_manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            continue
        try:
            reference_file = reference_for(packet["shot_id"])
            last_reference_file = end_reference_for(packet["shot_id"])
            print(f"reference: {reference_file or '<none>'}")
            print(f"end reference: {last_reference_file or '<same as first>'}")
            result = render_packet(packet, args.output / "shots", workflow=args.workflow,
                                    dry_run=args.dry_run, poll=args.poll, max_wait=args.max_wait,
                                    reference_file=reference_file,
                                    last_reference_file=last_reference_file)
            if result.get("outputs") and not args.dry_run:
                vertical_outputs = []
                for output in result["outputs"]:
                    source = Path(output)
                    vertical = source.with_name(source.stem + "_vertical.mp4")
                    normalize(source, vertical, focus=0.38)
                    vertical_outputs.append(str(vertical))
                result["raw_outputs"] = result["outputs"]
                result["outputs"] = vertical_outputs
                result["delivery_aspect_ratio"] = "9:16"
        except Exception as exc:
            result = {"shot_id": packet["shot_id"], "status": "failed", "error": str(exc)}
            print(f"FAILED: {exc}")
        previous_by_shot[packet["shot_id"]] = result
        completed_this_run += 1
        results = list(previous_by_shot.values())
        # Persist after every shot so a queue timeout or process interruption is resumable.
        manifest = {"project_id": project.project_id, "workflow": args.workflow,
                    "sequential": True, "completed_in_this_run": completed_this_run,
                    "results": results}
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {manifest_path}")
    return 1 if any(r.get("status") == "failed" for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
