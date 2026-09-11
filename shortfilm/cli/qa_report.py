"""Run the non-visual quality gates for a 30-second ad project."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from shortfilm.cli.validate_project import load


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: python -m shortfilm.cli.qa_report PROJECT.json REPORT.json")
        return 2
    project = load(Path(sys.argv[1]))
    errors = project.validate()
    warnings = []
    if len(project.shots) < 6 or len(project.shots) > 12:
        warnings.append("MVP recommends 6–12 shots for a 30-second ad")
    # Silent ads are a valid deliberate format. Only flag partially specified
    # speech, which usually means the audio policy is inconsistent.
    spoken = [shot for shot in project.shots if shot.dialogue_or_vo.strip()]
    if spoken and len(spoken) != len(project.shots):
        warnings.append("speech is present only in some shots; confirm this is intentional")
    if not any("品牌" in shot.story_beat or "产品" in shot.story_beat for shot in project.shots):
        warnings.append("no explicit product/brand beat found")
    consumption_phrases = ("喝一口", "喝咖啡", "饮用咖啡", "啜饮")
    negative_phrases = ("不饮用", "无饮用", "禁止饮用", "不喝")
    product_actions = sum(
        1
        for shot in project.shots
        if any(word in shot.subject_action for word in consumption_phrases)
        and not any(word in shot.subject_action for word in negative_phrases)
    )
    if product_actions > 2:
        errors.append(f"product consumption action appears {product_actions} times; story is becoming a drinking demo")
    if not any(any(word in shot.story_beat for word in ("失败", "卡住", "阻碍", "倒计时", "问题")) for shot in project.shots):
        warnings.append("no visible obstacle/turning pressure found in story beats")
    moving = [shot for shot in project.shots if shot.camera_move != "static"]
    if len(moving) < 3:
        warnings.append("camera language is under-designed: fewer than 3 moving shots")
    if len({shot.camera_move for shot in moving}) < 2 and len(moving) >= 3:
        warnings.append("camera language repeats one movement only; vary reveal/follow/emphasis")
    for previous, current in zip(project.shots, project.shots[1:]):
        if previous.screen_direction != "consistent" and current.screen_direction != "consistent" and previous.screen_direction != current.screen_direction:
            warnings.append(f"screen direction change between {previous.shot_id} and {current.shot_id} needs a motivated transition")
    report = {
        "project_id": project.project_id,
        "gates": {
            "story": "pass" if project.product and project.core_message else "fail",
            "storyboard": "pass" if not errors else "fail",
            "shot": "pending_visual_review",
            "final": "pending_render",
        },
        "errors": errors,
        "warnings": warnings,
        "manual_checks_required": ["character continuity", "product geometry", "motion quality", "audio/video sync"],
    }
    Path(sys.argv[2]).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
