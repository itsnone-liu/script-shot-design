"""Consumer for shot extensions V1 (schema/shot_extensions.schema.json).

Four optional per-shot fields — cast / scene_ref / dialogue / first_frame — plus
a seg-level ``asset_refs`` block naming the cards the seg's prompt_bible must be
synthesized from.  This module IS the consumption point promised by
ASSET_STORYBOARD_SCHEMA_V1 §3/§4:

* shot cast ⊆ seg card set (防串场); scene_ref must match the seg's scene card
* dialogue.speaker must be a declared cast member; the quoted line is compiled
  into the video prompt (H3 lip-sync method: 台词入 prompt 引号)
* first_frame carries keyframe_id + approval for the pay-gate (keyframe_gate.py
  enforces approval BEFORE any paid submission; validation here is structural)
* when asset_refs is present, the seg's hand-written prompt_bible is crosschecked
  against card synthesis — locks are a cache, cards are the source of truth.

Structural validation only never blocks on approval status: pending first_frame
is legal until render time.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from shortfilm.assets import load_asset_cards, synth_prompt_bible

APPROVAL_STATES = {"pending", "approved", "rejected"}
EXTENSION_KEYS = ("cast", "scene_ref", "dialogue", "first_frame")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _raw_shots(document: dict[str, Any]) -> list[dict[str, Any]]:
    shots = [x for x in document.get("internal_shots") or [] if isinstance(x, dict)]
    if shots:
        return shots
    return [x for x in document.get("timeline") or [] if isinstance(x, dict)]


def has_extensions(document: dict[str, Any]) -> bool:
    if document.get("asset_refs"):
        return True
    return any(any(key in shot for key in EXTENSION_KEYS) for shot in _raw_shots(document))


def _load_cards(refs: dict[str, Any], cards: dict[str, dict[str, Any]] | None) -> tuple[dict[str, dict[str, Any]] | None, str | None]:
    if cards is not None:
        return cards, None
    cards_path = _text(refs.get("cards_path"))
    if not cards_path:
        return None, "asset_refs present but neither cards nor cards_path is supplied"
    path = Path(cards_path)
    if not path.is_absolute():
        for base in (Path.cwd(), Path(__file__).resolve().parents[1]):
            candidate = base / path
            if candidate.is_file():
                path = candidate
                break
    if not path.is_file():
        return None, f"asset_refs.cards_path not found: {cards_path}"
    try:
        return load_asset_cards(path), None
    except ValueError as exc:
        return None, f"asset cards invalid: {exc}"


def validate_shot_extensions(
    document: dict[str, Any],
    cards: dict[str, dict[str, Any]] | None = None,
) -> list[str]:
    errors: list[str] = []
    refs = document.get("asset_refs") or {}
    seg_cast = [x.strip() for x in refs.get("cast") or [] if str(x).strip()]
    seg_scene = _text(refs.get("scene_ref"))

    if refs:
        cards, load_error = _load_cards(refs, cards)
        if load_error:
            return [load_error]
        for card_id in [*seg_cast, seg_scene]:
            if card_id and card_id not in cards:
                errors.append(f"asset_refs: unknown card id {card_id}")
        if seg_scene and seg_scene in cards and cards[seg_scene].get("type") != "scene":
            errors.append(f"asset_refs.scene_ref must reference a type=scene card, got {seg_scene}")
        for card_id in seg_cast:
            if card_id in cards and cards[card_id].get("type") == "scene":
                errors.append(f"asset_refs.cast cannot contain the scene card {card_id}")
        if not errors and seg_cast and seg_scene:
            # locks are a cache: the seg's prompt_bible must match card synthesis
            # (crosscheck semantics: env/light/palette/subject drift = blocking
            # error; never_show wording gaps = migration diff, surfaced by
            # synth_bible --check, pending card rewording review)
            from shortfilm.assets import crosscheck_bible

            report = crosscheck_bible(document, cards, seg_cast, seg_scene, document.get("staging") or {})
            errors.extend(report["errors"])

    shots = _raw_shots(document)
    shot_ids = [_text(shot.get("shot_id")) for shot in shots]
    for index, shot in enumerate(shots):
        label = _text(shot.get("shot_id")) or f"shot {index}"

        shot_cast = [x.strip() for x in shot.get("cast") or [] if str(x).strip()]
        if shot_cast:
            if cards is not None:
                for card_id in shot_cast:
                    if card_id not in cards:
                        errors.append(f"{label}: cast references unknown card {card_id}")
            if seg_cast:
                off_screen = [x for x in shot_cast if x not in seg_cast]
                if off_screen:
                    errors.append(f"{label}: cast not declared in seg asset_refs (串场): {', '.join(off_screen)}")
            elif cards is not None:
                pass  # no seg-level refs: shot cast stands alone, card existence checked above

        shot_scene = _text(shot.get("scene_ref"))
        if shot_scene:
            if cards is not None and shot_scene not in cards:
                errors.append(f"{label}: scene_ref references unknown card {shot_scene}")
            if seg_scene and shot_scene != seg_scene:
                errors.append(
                    f"{label}: scene_ref {shot_scene} differs from seg scene {seg_scene} "
                    f"(V1 segs are single-scene; a scene change must be its own seg)"
                )

        dialogue = shot.get("dialogue") or {}
        if _text(dialogue.get("line")):
            speaker = _text(dialogue.get("speaker"))
            if not speaker:
                errors.append(f"{label}: dialogue.line requires dialogue.speaker")
            else:
                if cards is not None and speaker not in cards:
                    errors.append(f"{label}: dialogue.speaker references unknown card {speaker}")
                if shot_cast and speaker not in shot_cast:
                    errors.append(f"{label}: dialogue.speaker {speaker} is not in this shot's cast")
                elif not shot_cast and seg_cast and speaker not in seg_cast:
                    errors.append(f"{label}: dialogue.speaker {speaker} is not in seg asset_refs cast")

        first_frame = shot.get("first_frame") or {}
        if first_frame:
            if not _text(first_frame.get("keyframe_id")):
                errors.append(f"{label}: first_frame requires keyframe_id")
            approval = _text(first_frame.get("approval"))
            if approval and approval not in APPROVAL_STATES:
                errors.append(f"{label}: first_frame.approval must be one of {sorted(APPROVAL_STATES)}")
            continuity = _text(first_frame.get("continuity_from"))
            if continuity and continuity != "opening" and continuity not in shot_ids[:index]:
                errors.append(
                    f"{label}: first_frame.continuity_from must be 'opening' or a previous shot_id, got {continuity}"
                )
    return errors


def compile_dialogue_line(shot: dict[str, Any]) -> str:
    """H3 lip-sync method: the quoted line enters the video prompt verbatim."""
    dialogue = shot.get("dialogue") or {}
    line = _text(dialogue.get("line"))
    if not line:
        return ""
    speaker = _text(dialogue.get("speaker")) or "the speaker"
    return f'Dialogue: {speaker} says: "{line}"'
