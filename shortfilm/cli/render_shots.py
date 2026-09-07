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
    reference_file = ""
    if args.reference_image:
        if args.dry_run:
            reference_file = f"<upload:{args.reference_image}>"
        else:
            key = rh_adapter.rh_task.load_api_key()
            if not key:
                print("reference image requested but RH API key unavailable")
                return 1
            reference_file = rh_adapter.rh_task.upload_file(key, args.reference_image)
            print(f"reference uploaded once: {args.reference_image.name}")
    raw_packets = []
    for shot in project.shots:
        prompt_parts = [
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
    for packet in raw_packets[args.start:end]:
        print(f"\n=== {packet['shot_id']} ({packet['duration']}s) ===")
        try:
            result = render_packet(packet, args.output / "shots", workflow=args.workflow,
                                   dry_run=args.dry_run, poll=args.poll, max_wait=args.max_wait,
                                   reference_file=reference_file)
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
        results = list(previous_by_shot.values())
        # Persist after every shot so a queue timeout or process interruption is resumable.
        manifest = {"project_id": project.project_id, "workflow": args.workflow,
                    "sequential": True, "completed_in_this_run": len(results),
                    "results": results}
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {manifest_path}")
    return 1 if any(r.get("status") == "failed" for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
