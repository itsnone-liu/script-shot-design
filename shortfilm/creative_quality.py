"""Creative and cinematic quality gates for the 821 story-first pipeline.

These checks do not pretend to score taste deterministically. They make the LLM
externalize the choices that prevent a merely valid causal chain from becoming a
flat, expected sequence, and the on-set decisions an amnesiac video model cannot
infer between shots.
"""
from __future__ import annotations

from typing import Any

CREATIVE_STRATEGY_FIELDS = (
    "audience_assumption",
    "expectation_break",
    "creative_engine",
    "world_rule",
    "visual_motif",
    "escalation_ladder",
    "reveal_design",
    "ending_reframe",
    "product_truth",
    "cliche_rejected",
)

CREATIVE_ENGINES = {
    "world_collision",
    "impossible_rule",
    "misdirection_reveal",
    "visual_metaphor",
    "ritual_escalation",
    "role_reversal",
    "constraint_game",
    "cause_effect_chain",
    "perspective_shift",
    "emotional_contradiction",
}

STORY_DESIGN_FIELDS = (
    "world_rule",
    "visual_motif_progression",
    "information_strategy",
    "escalation_logic",
    "ending_reframe",
)

BEAT_DESIGN_FIELDS = (
    "audience_question",
    "new_information",
    "motif_state",
    "escalation_level",
)

SHOT_DESIGN_FIELDS = (
    "narrative_job",
    "audience_knowledge",
    "composition_logic",
    "blocking_map",
    "performance_detail",
    "light_motivation",
    "event_budget",
)


def _issue(severity: str, code: str, **details: Any) -> dict[str, Any]:
    return {"severity": severity, "code": code, **details}


def validate_creative_strategy(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Require explicit novelty mechanics before a concept can become a story."""
    issues: list[dict[str, Any]] = []
    candidates = document.get("candidates", []) if isinstance(document, dict) else []
    if not isinstance(candidates, list) or len(candidates) < 3:
        return [_issue("blocker", "too_few_concepts", message="at least three concepts required")]

    seen_engines: list[str] = []
    seen_breaks: set[str] = set()
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            issues.append(_issue("blocker", "invalid_concept", concept=index))
            continue
        cid = candidate.get("id", index)
        strategy = candidate.get("creative_strategy")
        if not isinstance(strategy, dict):
            issues.append(_issue("blocker", "missing_creative_strategy", concept=cid))
            continue
        for field in CREATIVE_STRATEGY_FIELDS:
            value = strategy.get(field)
            if value in (None, "", []):
                issues.append(_issue("blocker", "missing_creative_strategy_field", concept=cid, field=field))
        engine = str(strategy.get("creative_engine", "")).strip()
        if engine and engine not in CREATIVE_ENGINES:
            issues.append(_issue("blocker", "unsupported_creative_engine", concept=cid, engine=engine))
        if engine:
            seen_engines.append(engine)
        ladder = strategy.get("escalation_ladder") or []
        if not isinstance(ladder, list) or len(ladder) < 3:
            issues.append(_issue("blocker", "weak_escalation_ladder", concept=cid, message="three escalating turns required"))
        reveal = strategy.get("reveal_design") or {}
        if not isinstance(reveal, dict) or not all(reveal.get(k) for k in ("withhold", "clue", "reveal")):
            issues.append(_issue("blocker", "incomplete_reveal_design", concept=cid))
        expectation_break = str(strategy.get("expectation_break", "")).strip().lower()
        if expectation_break:
            if expectation_break in seen_breaks:
                issues.append(_issue("warning", "duplicate_expectation_break", concept=cid))
            seen_breaks.add(expectation_break)

    if len(set(seen_engines)) < min(3, len(candidates)):
        issues.append(_issue(
            "blocker",
            "concepts_not_mechanically_distinct",
            message="concept candidates must use at least three different creative engines",
        ))
    return issues


def validate_story_design(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Keep the selected novelty mechanism alive after concept selection."""
    issues: list[dict[str, Any]] = []
    for field in STORY_DESIGN_FIELDS:
        if document.get(field) in (None, "", []):
            issues.append(_issue("blocker", "missing_story_design_field", field=field))
    return issues


def validate_beat_design(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Require information change and escalation, not only causal completeness."""
    issues: list[dict[str, Any]] = []
    beats = document.get("beats", []) if isinstance(document, dict) else []
    levels: list[float] = []
    for index, beat in enumerate(beats if isinstance(beats, list) else []):
        for field in BEAT_DESIGN_FIELDS:
            if beat.get(field) in (None, "", []):
                issues.append(_issue("blocker", "missing_beat_design_field", beat=beat.get("id", index), field=field))
        level = beat.get("escalation_level")
        if isinstance(level, (int, float)):
            levels.append(float(level))
    if levels and all(current <= previous for previous, current in zip(levels, levels[1:])):
        issues.append(_issue("blocker", "no_escalation_change", message="at least one later beat must raise the escalation level"))
    return issues


def validate_cinematic_scene_design(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate shot-level information control and AI on-set instructions."""
    issues: list[dict[str, Any]] = []
    scenes = document.get("scenes", []) if isinstance(document, dict) else []
    if not isinstance(scenes, list) or not scenes:
        return [_issue("blocker", "missing_scenes")]

    composition_sequence: list[str] = []
    for scene_index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            issues.append(_issue("blocker", "invalid_scene", scene=scene_index))
            continue
        shots = scene.get("shot_list") or scene.get("editorial_shots") or []
        if not isinstance(shots, list) or not shots:
            issues.append(_issue("blocker", "missing_editorial_shots", scene=scene.get("id", scene_index)))
            continue
        for shot_index, shot in enumerate(shots):
            sid = shot.get("shot_id") or f"{scene.get('id', scene_index)}.{shot_index}"
            if not isinstance(shot, dict):
                issues.append(_issue("blocker", "invalid_editorial_shot", shot=sid))
                continue
            design = shot.get("cinematic_design")
            if not isinstance(design, dict):
                issues.append(_issue("blocker", "missing_cinematic_design", shot=sid))
                continue
            for field in SHOT_DESIGN_FIELDS:
                value = design.get(field)
                if value in (None, "", []):
                    issues.append(_issue("blocker", "missing_cinematic_design_field", shot=sid, field=field))
            blocking = design.get("blocking_map") or {}
            if not isinstance(blocking, dict) or not all(blocking.get(k) for k in ("subject_position", "movement_path", "camera_position", "screen_direction")):
                issues.append(_issue("blocker", "incomplete_blocking_map", shot=sid))
            light = design.get("light_motivation") or {}
            if not isinstance(light, dict) or not all(light.get(k) for k in ("source", "direction", "color_temperature")):
                issues.append(_issue("blocker", "unmotivated_light", shot=sid))
            budget = design.get("event_budget") or {}
            concurrent = budget.get("max_concurrent_events") if isinstance(budget, dict) else None
            if not isinstance(concurrent, (int, float)) or concurrent < 1 or concurrent > 3:
                issues.append(_issue("blocker", "visual_event_overload", shot=sid, max_concurrent_events=concurrent))
            composition = str(design.get("composition_logic", "")).strip().lower()
            if composition:
                composition_sequence.append(composition)

    if len(composition_sequence) >= 4 and len(set(composition_sequence)) == 1:
        issues.append(_issue("warning", "repetitive_composition_logic", count=len(composition_sequence)))
    return issues
