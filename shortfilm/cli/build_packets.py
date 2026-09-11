"""Build deterministic prompt packets and an edit timeline from a project JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from shortfilm.cli.validate_project import load
from shortfilm.knowledge.runtime import get_card


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: python -m shortfilm.cli.build_packets PROJECT.json OUTPUT_DIR")
        return 2
    project_path, output_dir = Path(sys.argv[1]), Path(sys.argv[2])
    project = load(project_path)
    card = get_card()
    errors = project.validate()
    if errors:
        print("Project is invalid; no packets generated:")
        print("\n".join(f"- {e}" for e in errors))
        return 1
    output_dir.mkdir(parents=True, exist_ok=True)

    packets = []
    timeline = []
    cursor = 0.0
    for shot in project.shots:
        assembled_prompt = "; ".join(filter(None, [
            project.visual_style,
            card["prompt_constraints"]["positive"],
            f"{shot.shot_size}, {shot.angle} angle, {shot.composition} composition",
            f"single attention subject: {shot.attention_subject}; product visibility: {shot.product_visibility}",
            f"camera movement: {shot.camera_move}",
            f"movement intent: {shot.movement_intent}, speed: {shot.movement_speed}",
            f"start framing: {shot.start_framing}; end framing: {shot.end_framing}",
            f"screen direction: {shot.screen_direction}; stabilization: {shot.stabilization}",
            f"action: {shot.subject_action}",
            f"lighting: {shot.lighting}",
            f"gaze: {shot.gaze}",
            "preserve identity, costume, screen direction and product geometry",
            "no text, no logo, no watermark, no extra limbs",
        ]))
        prompt = shot.generation_prompt or assembled_prompt
        packets.append({
            "shot_id": shot.shot_id,
            "workflow": shot.generation_workflow,
            "duration": shot.duration,
            "reference_assets": shot.reference_assets,
            "prompt": prompt,
            "negative_prompt": "; ".join(["deformed hands, unstable face, unreadable text, logo artifacts, flicker, jump cut", card["prompt_constraints"]["negative"]]),
            "acceptance_tests": shot.acceptance_tests,
            "movement_plan": {
                "move": shot.camera_move,
                "intent": shot.movement_intent,
                "speed": shot.movement_speed,
                "start_framing": shot.start_framing,
                "end_framing": shot.end_framing,
                "stabilization": shot.stabilization,
                "screen_direction": shot.screen_direction,
                "transition_to_next": shot.transition_to_next,
            },
        })
        timeline.append({"shot_id": shot.shot_id, "start": round(cursor, 3), "end": round(cursor + shot.duration, 3)})
        cursor += shot.duration

    (output_dir / "prompt_packets.json").write_text(json.dumps(packets, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "edit_timeline.json").write_text(json.dumps({
        "project_id": project.project_id,
        "aspect_ratio": project.aspect_ratio,
        "duration": project.duration_target,
        "clips": timeline,
        "audio": {"voiceover": "pending", "music": "pending", "mix_target_lufs": -14},
        "overlays": {"captions": "pending", "logo": "post-production"},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {len(packets)} prompt packets and timeline in {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
