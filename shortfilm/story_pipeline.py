"""LLM-assisted story/script pipeline with deterministic gates.

The LLM is responsible for creative expansion and revision. This module owns
portable prompts, artifact contracts, provider adaptation, and deterministic
validation so a provider cannot silently bypass the Story/Script gates.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent

@dataclass
class LLMConfig:
    base_url: str = "https://api.deepseek.com/v1/chat/completions"
    model: str = "deepseek-chat"
    api_key: str = ""
    timeout: int = 180

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            base_url=os.getenv("EIGHT21_LLM_URL", os.getenv("OPENAI_BASE_URL", cls.base_url)),
            model=os.getenv("EIGHT21_LLM_MODEL", os.getenv("OPENAI_MODEL", cls.model)),
            api_key=os.getenv("EIGHT21_LLM_API_KEY", os.getenv("OPENAI_API_KEY", "")),
        )


def _json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\\s*|\\s*```$", "", text, flags=re.I | re.S)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("LLM response did not contain a JSON object")
    return json.loads(text[start:end + 1])


def call_llm(prompt: str, config: LLMConfig | None = None) -> dict[str, Any]:
    cfg = config or LLMConfig.from_env()
    if not cfg.api_key:
        raise RuntimeError("missing EIGHT21_LLM_API_KEY or OPENAI_API_KEY")
    payload = json.dumps({
        "model": cfg.model,
        "temperature": 0.8,
        "messages": [
            {"role": "system", "content": "You are a senior short-film screenwriter. Return valid JSON only."},
            {"role": "user", "content": prompt},
        ],
    }).encode("utf-8")
    req = urllib.request.Request(cfg.base_url, payload, {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {cfg.api_key}",
    })
    with urllib.request.urlopen(req, timeout=cfg.timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    return _json(body["choices"][0]["message"]["content"])


def build_prompt(brief: dict[str, Any], reference: dict[str, Any], rules: list[dict[str, Any]]) -> str:
    return f"""Create a complete structured short-film script package.

Return one JSON object with keys: concept_candidates (3 items), story_statement,
beat_sheet (4-9 beats), scene_cards, script_markdown, reviews, diagnostics.
First establish concept and causality, then let story/editorial rhythm determine a motivated shot list in scene_cards. Do not pre-divide the film into equal 10-second blocks.

NON-NEGOTIABLES:
- one protagonist and one main goal unless the brief says otherwise;
- every beat has state_in, visible_event, character_choice, state_out, causal_hook;
- the product/theme changes observation, choice, action, or result; it is not decoration;
- no sudden success, unexplained inspiration, or dialogue describing visible action;
- separate visual spectacle from story function; use spectacle only when it advances the beat;
- respect duration, platform, dialogue policy, safety and production constraints;
- in scene_cards include an editorial shot list whose durations and cuts come from story needs, not equal-duration templates;
- each internal shot may have one primary camera move; after an explicit cut the next shot may use a different move;
- treat MiniMax 5-15 second generation calls as later technical containers that may include multiple explicit internal cuts;
- mark uncertainty and production risks instead of inventing facts.

CREATIVE BRIEF:
{json.dumps(brief, ensure_ascii=False, indent=2)}

REFERENCE AD ANALYSIS (structure may transfer, surface details must not be copied):
{json.dumps(reference, ensure_ascii=False, indent=2)}

KNOWN RULES:
{json.dumps(rules, ensure_ascii=False, indent=2)}

For reviews, use roles StoryEditor, AudienceAdvocate, BrandStrategist,
ProductionEditor, AdversarialReviewer. Each must list issues with artifact/field,
severity, and concrete rewrite advice. Diagnostics must use blocker/warning/note.
"""


def diagnose(package: dict[str, Any], brief: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    beats = package.get("beat_sheet") or []
    if len(beats) < 4:
        errors.append({"severity": "blocker", "code": "too_few_beats", "message": "at least four beats required"})
    required = ("state_in", "visible_event", "character_choice", "state_out", "causal_hook")
    for i, beat in enumerate(beats):
        for field in required:
            if not beat.get(field):
                errors.append({"severity": "blocker", "code": "missing_beat_field", "beat": i, "field": field})
    script = str(package.get("script_markdown", ""))
    if not script:
        errors.append({"severity": "blocker", "code": "missing_script", "message": "script_markdown is empty"})
    duration = int(brief.get("duration_sec", 30))
    if duration <= 0:
        errors.append({"severity": "blocker", "code": "invalid_duration"})
    product_actions = len(re.findall(r"喝|饮用|拿起|展示产品|产品特写", script))
    if product_actions > 2:
        errors.append({"severity": "warning", "code": "repeated_product_action", "count": product_actions})
    if re.search(r"突然成功|立刻成功|灵感爆发|一键完成", script):
        errors.append({"severity": "blocker", "code": "sudden_success"})
    return {"status": "block" if any(x["severity"] == "blocker" for x in errors) else "pass", "issues": errors}


def run_pipeline(brief: dict[str, Any], reference: dict[str, Any], rules: list[dict[str, Any]], provider: Callable[[str], dict[str, Any]] | None = None) -> dict[str, Any]:
    prompt = build_prompt(brief, reference, rules)
    package = (provider or call_llm)(prompt)
    package["diagnostics"] = diagnose(package, brief)
    package["pipeline"] = {"provider": "custom" if provider else "openai-compatible", "story_gate": package["diagnostics"]["status"]}
    return package


def write_package(package: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for key in ("concept_candidates", "story_statement", "beat_sheet", "scene_cards", "reviews", "diagnostics", "pipeline"):
        value = package.get(key)
        if value is not None:
            (out_dir / f"{key}.json").write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    if package.get("script_markdown") is not None:
        (out_dir / "script.md").write_text(str(package["script_markdown"]), encoding="utf-8")
