"""Stage definitions for the 821 story pipeline.

Each stage receives prior validated artifacts and returns one JSON document.
The runner may use these prompts with any LLMClient implementation.
"""
from __future__ import annotations
import json
from typing import Any

STAGES = (
    "concept_candidates", "story_statement", "beat_sheet",
    "scene_cards", "script_markdown", "reviews",
)

STAGE_INSTRUCTIONS = {
    "concept_candidates": """Generate 3-5 concepts that are mechanically different, not cosmetic variations. Each candidate must include creative_strategy with: audience_assumption; expectation_break; one creative_engine chosen from world_collision/impossible_rule/misdirection_reveal/visual_metaphor/ritual_escalation/role_reversal/constraint_game/cause_effect_chain/perspective_shift/emotional_contradiction; a precise world_rule; a recurring visual_motif; a three-step escalation_ladder; reveal_design {withhold, clue, reveal}; ending_reframe; product_truth; and cliche_rejected. The strange choice must express the theme or product truth rather than exist as decoration. Also include hook, tension, minimax_visual_fit and risk_flags.""",
    "story_statement": "Select or hybridize one concept into a story contract: logline, protagonist desire, obstacle, stakes, arc, twist, theme, emotion curve, governing world rule, visual motif progression, information strategy, escalation logic and ending reframe. Preserve the selected expectation break; do not normalize it into a familiar problem-solution story.",
    "beat_sheet": "Turn the story contract into 5-7 state-transition beats. Every beat must contain state_in, visible_event, character_choice, state_out, causal_hook, duration_sec, audience_question, new_information, motif_state and escalation_level. At least one beat must redirect the audience's interpretation, and each escalation must change the situation rather than repeat the prior action more loudly.",
    "scene_cards": """Turn beats into a script-first editorial design: filmable scene cards plus a motivated shot list. Let story information, emotion, action, shape, color and sound determine shot count, duration and cut type; never pre-divide into equal technical blocks. Every shot must include start/end time, framing, attention subject, action, independent camera move, transition_in, match point where relevant, audio cue and exit state. Every shot must also include cinematic_design: narrative_job; audience_knowledge {knows, does_not_know, question}; composition_logic; blocking_map {subject_position, movement_path, camera_position, screen_direction}; foreground/midground/background use; performance_detail with an observable micro-action and, when useful, reaction-before-protagonist; light_motivation {source, direction, color_temperature}; and event_budget {max_concurrent_events from 1 to 3, timed_events}. Treat AI as literal and amnesiac: write continuity and human imperfection explicitly. Camera movement must change information, pressure, intimacy or reveal; otherwise keep it still or use restrained human breathing rather than default gimbal smoothness. MiniMax 5-15 second containers are assigned only after this design is approved.""",
    "script_markdown": "Write a readable shootable script from the approved editorial scene cards. Preserve the expectation break, world rule, motif progression, information withholding/reveal, escalation and ending reframe. Preserve every motivated cut and shot duration; do not flatten the film into one-take blocks and do not invent new causality. Separate image, blocking/performance, camera/composition, light, cut, dialogue/VO, sound, and post-production text.",
    "reviews": "Review the package as StoryEditor, AudienceAdvocate, BrandStrategist, Cinematographer, PerformanceDirector, ProductionEditor, and AdversarialReviewer. Explicitly test whether the first image creates a question, the middle escalates or changes interpretation, the ending recontextualizes an earlier image, each shot controls information, performance includes human micro-behavior, light is physically sourced, and no shot exceeds three concurrent visual events. Give field paths, severity, and rewrite advice.",
}

def messages_for(stage: str, brief: dict[str, Any], prior: dict[str, Any], reference: dict[str, Any], rules: list[dict[str, Any]], errors: list[dict[str, Any]] | None = None) -> list[dict[str, str]]:
    repair = ""
    if errors:
        repair = "\nREPAIR THESE VALIDATION ISSUES WITHOUT CHANGING VALID CONTENT:\n" + json.dumps(errors, ensure_ascii=False)
    return [
        {"role": "system", "content": "You are a senior short-film screenwriter. Return JSON only; never wrap it in markdown fences."},
        {"role": "user", "content": json.dumps({
            "task": STAGE_INSTRUCTIONS[stage], "brief": brief, "prior_artifacts": prior,
            "reference_analysis": reference, "rules": rules,
            "constraints": ["respect the brief duration", "make cause and effect visible", "create curiosity through an expectation gap rather than mere obscurity", "make every escalation alter stakes, knowledge, power or physical state instead of repeating an action", "make the ending reframe or pay off an earlier image", "let screenplay and editorial rhythm determine shots before choosing generation containers", "allow motivated internal cuts inside a MiniMax 5-15 second container", "apply one primary camera move per internal shot, not per whole container", "treat the video model as literal and amnesiac: specify blocking, micro-performance, continuity and motivated light", "budget no more than three concurrent visual events per shot", "use camera and composition to control information, not as decorative motion", "do not copy reference surface details", "flag uncertainty instead of inventing facts"],
        }, ensure_ascii=False) + repair},
    ]
