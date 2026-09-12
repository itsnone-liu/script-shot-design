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
    "concept_candidates": "Generate 3-5 genuinely different story concepts. Vary the protagonist goal, conflict, theme/product role, and ending. Include minimax_visual_fit and risk_flags.",
    "story_statement": "Select or develop one concept into a story contract: logline, protagonist desire, obstacle, stakes, arc, twist, theme, and emotion curve.",
    "beat_sheet": "Turn the story contract into 5-7 state-transition beats. Every beat must contain state_in, visible_event, character_choice, state_out, causal_hook, duration_sec.",
    "scene_cards": "Turn beats into filmable scene cards. Keep one main line, make visual information explicit, and include shot_hints and audio_notes.",
    "script_markdown": "Write a readable shootable script from the scene cards. Do not invent new causality. Separate image, action, dialogue/VO, sound, and post-production text.",
    "reviews": "Review the package as StoryEditor, AudienceAdvocate, BrandStrategist, ProductionEditor, and AdversarialReviewer. Give field paths, severity, and rewrite advice.",
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
            "constraints": ["respect the brief duration", "make cause and effect visible", "do not copy reference surface details", "flag uncertainty instead of inventing facts"],
        }, ensure_ascii=False) + repair},
    ]
