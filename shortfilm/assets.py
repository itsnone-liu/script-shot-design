"""Asset cards -> prompt_bible synthesis (implements ASSET_STORYBOARD_SCHEMA_V1 §4).

The documented formula:
    subject_lock     = sum(character card subject_lock_text) + seg staging suffix
    environment_lock = scene card environment_lock_text
    lighting_lock    = scene card lighting_lock_text
    palette_lock     = scene card palette_lock_text
    material_lock    = ordered union(material fragments) + seg staging suffix
    never_show       = global never + sum(card continuity_rules mapped) + staging extras

Synthesis is a pure function: same cards + same staging -> same lock text, so it
can be diffed and regression-tested (schema §4).  The seg's hand-written lock is
a CACHE: cards are the source of truth.  crosscheck_bible() reports the diff
between a legacy seg's hand-written prompt_bible and the synthesized one —
differences are semantic loss from the card split and must be fixed to zero
(schema §5 migration rule).

Stdlib only, dependency-free, same as the rest of shortfilm/.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

BASE_NEVER_SHOW = ["readable text", "logo", "watermark"]
_MODESTY_CLAUSE = "fully clothed in every frame"
_NEGATIVE_PREFIXES = ("no ", "never a ", "never ")


def load_asset_cards(path: str | Path) -> dict[str, dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cards = data.get("cards") if isinstance(data, dict) else data
    if not isinstance(cards, list):
        raise ValueError(f"{path}: expected a 'cards' list")
    out: dict[str, dict[str, Any]] = {}
    for card in cards:
        card_id = str(card.get("id") or "")
        if not card_id:
            raise ValueError(f"{path}: card without id")
        if card_id in out:
            raise ValueError(f"{path}: duplicate card id {card_id}")
        out[card_id] = card
    return out


def _fragments(text: str) -> list[str]:
    return [p.strip() for part in text.split(";") for p in part.split(",") if p.strip()]


def _ordered_union(items: list[str]) -> list[str]:
    seen: dict[str, None] = {}
    for item in items:
        for fragment in _fragments(item):
            seen.setdefault(fragment.lower(), fragment)
    return list(seen.values())


def _hoist_modesty(texts: list[str]) -> tuple[list[str], bool]:
    """Hoist a trailing 'fully clothed in every frame' clause out of every
    character text so a multi-character join reads 'both/all fully clothed...'
    once (couple30 segA convention).  Only fires when EVERY text carries it."""
    if len(texts) < 2:
        return texts, False
    suffix = "; " + _MODESTY_CLAUSE
    if not all(t.rstrip().endswith(_MODESTY_CLAUSE) for t in texts):
        return texts, False
    return [t.rstrip()[: -len(_MODESTY_CLAUSE)].rstrip().rstrip(";").rstrip() for t in texts], True


def rule_to_never(rule: str) -> str | None:
    """Map a card continuity rule to a never_show term; positive rules
    (e.g. 'curtain openness stays consistent') return None and are not
    compiled into never_show."""
    r = str(rule).strip()
    lower = r.lower()
    prefix = next((p for p in _NEGATIVE_PREFIXES if lower.startswith(p)), None)
    if prefix is None:
        return None
    term = r[len(prefix):].strip()
    if "(" in term and ")" in term:
        term = term[term.index("(") + 1: term.rindex(")")]
        term = term.split("=")[0].strip()
    return term or None


def synth_prompt_bible(
    cards: dict[str, dict[str, Any]],
    cast_ids: list[str],
    scene_ref: str,
    staging: dict[str, Any] | None = None,
) -> dict[str, Any]:
    staging = staging or {}
    errors: list[str] = []
    for card_id in [*cast_ids, scene_ref]:
        if card_id not in cards:
            errors.append(f"unknown asset card id: {card_id}")
    if errors:
        raise ValueError("; ".join(errors))
    scene = cards[scene_ref]
    if scene.get("type") != "scene":
        raise ValueError(f"{scene_ref}: scene_ref must reference a type=scene card")
    chars = []
    for card_id in cast_ids:
        card = cards[card_id]
        if card.get("type") == "scene":
            raise ValueError(f"{card_id}: scene card cannot appear in cast")
        chars.append(card)
    if not chars and not staging.get("subject_override"):
        raise ValueError("cast is empty: character pieces need cast ids (or staging.subject_override)")

    fragments = {c["id"]: c.get("prompt_fragments") or {} for c in chars}
    scene_f = scene.get("prompt_fragments") or {}

    # subject_lock
    texts = [str(f.get("subject_lock_text") or "") for f in fragments.values()]
    if any(not t for t in texts):
        missing = [cid for cid, f in fragments.items() if not f.get("subject_lock_text")]
        raise ValueError(f"character cards missing subject_lock_text: {', '.join(missing)}")
    hoisted_texts, hoisted = _hoist_modesty(texts)
    if staging.get("subject_override"):
        subject = str(staging["subject_override"])
    elif len(hoisted_texts) == 1:
        subject = hoisted_texts[0]
    else:
        head = "; ".join(hoisted_texts[:-1])
        count_word = {2: "two", 3: "three", 4: "four", 5: "five"}.get(len(hoisted_texts), str(len(hoisted_texts)))
        subject = f"exactly {count_word} people: {head}; and {hoisted_texts[-1]}"
    if hoisted:
        quantifier = "both" if len(hoisted_texts) == 2 else "all"
        subject += f"; {quantifier} {_MODESTY_CLAUSE}"
    if staging.get("subject_suffix"):
        subject += f"; {str(staging['subject_suffix']).strip()}"

    # scene-sourced locks (pure card text, byte-for-byte)
    for field in ("environment_lock_text", "lighting_lock_text", "palette_lock_text"):
        if not scene_f.get(field):
            raise ValueError(f"{scene_ref}: scene card missing {field}")

    # material_lock: ordered union of scene + character fragments, staging suffix
    material_parts = [str(scene_f.get("material_lock_text") or "")] + [
        str(f.get("material_lock_text") or "") for f in fragments.values()
    ]
    material_body = ", ".join(_ordered_union(material_parts))
    material = material_body
    if staging.get("material_suffix"):
        material += f"; {str(staging['material_suffix']).strip()}"

    # never_show
    never: list[str] = list(BASE_NEVER_SHOW)
    for card in [*chars, scene]:
        for rule in card.get("continuity_rules") or []:
            term = rule_to_never(str(rule))
            if term and term.lower() not in {n.lower() for n in never}:
                never.append(term)
    for extra in staging.get("never_show_extra") or []:
        if str(extra).lower() not in {n.lower() for n in never}:
            never.append(str(extra))

    return {
        "subject_lock": subject,
        "environment_lock": str(scene_f["environment_lock_text"]),
        "lighting_lock": str(scene_f["lighting_lock_text"]),
        "palette_lock": str(scene_f["palette_lock_text"]),
        "material_lock": material,
        "never_show": never,
        "_synthesis": {
            "cast": list(cast_ids),
            "scene_ref": scene_ref,
            "modesty_hoisted": hoisted,
            "material_fragment_count": len(_ordered_union(material_parts)),
        },
    }


def _never_matches(term: str, items: list[str]) -> bool:
    tl = term.lower()
    for item in items:
        il = item.lower()
        if tl == il or il.startswith(tl) or tl.startswith(il):
            return True
    return False


def crosscheck_bible(
    seg: dict[str, Any],
    cards: dict[str, dict[str, Any]],
    cast_ids: list[str],
    scene_ref: str,
    staging: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Diff a legacy seg's hand-written prompt_bible against the synthesized
    one.  errors = must fix to zero diff; diffs = card-side gaps to fix;
    info = acceptable piece-specific extras / order notes."""
    synthesized = synth_prompt_bible(cards, cast_ids, scene_ref, staging)
    bible = seg.get("prompt_bible") or {}
    errors: list[str] = []
    diffs: list[str] = []
    info: list[str] = []
    for field in ("environment_lock", "lighting_lock", "palette_lock"):
        if str(bible.get(field) or "") != synthesized[field]:
            errors.append(f"{field}: hand-written text differs from scene card source")
    if str(bible.get("subject_lock") or "") != synthesized["subject_lock"]:
        errors.append(
            "subject_lock: hand-written differs from card synthesis\n"
            f"  hand:     {bible.get('subject_lock')}\n  synthesized: {synthesized['subject_lock']}"
        )
    hand_material = str(bible.get("material_lock") or "")
    hand_set = {f.lower() for f in _fragments(hand_material.split(";")[0])}
    syn_set = {f.lower() for f in _fragments(synthesized["material_lock"].split(";")[0])}
    if hand_set != syn_set:
        diffs.append(
            "material_lock fragment sets differ: "
            f"hand-only={sorted(hand_set - syn_set)} synth-only={sorted(syn_set - hand_set)}"
        )
    elif hand_material != synthesized["material_lock"]:
        info.append("material_lock: same fragments, different order/suffix wording")
    seg_never = [str(x) for x in bible.get("never_show") or []]
    for term in synthesized["never_show"]:
        if not _never_matches(term, seg_never):
            diffs.append(f"never_show: card-derived term not present in seg: {term}")
    syn_terms = {t.lower() for t in synthesized["never_show"]}
    for item in seg_never:
        if not _never_matches(item, [t for t in synthesized["never_show"]]):
            info.append(f"never_show: seg-only item (piece-specific, add to staging extras): {item}")
    return {"errors": errors, "diffs": diffs, "info": info, "synthesized": synthesized}


def build_refs_manifest(cards_path: str | Path, identity_root: str | Path) -> dict[str, Any]:
    """Content hashes for every card's reference chain (approval-gate input).
    Resolves <identity_root>/<canonical_chain_version>/* image files."""
    cards = load_asset_cards(cards_path)
    root = Path(identity_root)
    manifest: dict[str, Any] = {"schema_version": "asset-refs-manifest-v1", "cards": {}}
    for card_id, card in cards.items():
        refs = card.get("refs") or {}
        chain = str(refs.get("canonical_chain_version") or "")
        entry: dict[str, Any] = {"canonical_chain_version": chain, "files": {}}
        if chain:
            chain_dir = root / chain
            files = sorted(p for p in chain_dir.glob("*") if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"})
            if not files:
                raise ValueError(f"{card_id}: no reference images under {chain_dir}")
            for path in files:
                entry["files"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        card_bytes = json.dumps(card, ensure_ascii=False, sort_keys=True).encode("utf-8")
        entry["card_sha256"] = hashlib.sha256(card_bytes).hexdigest()
        manifest["cards"][card_id] = entry
    return manifest
