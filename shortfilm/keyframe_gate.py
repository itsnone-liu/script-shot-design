"""First-frame pay-gate: no paid video submission unless every shot's keyframe
is user-approved AND the file on disk still hashes to the approved content.

Closes the gap found in the coffee30 v1 postmortem: the 5-keyframe approval was
a process convention (approval recorded in review feedback text), not enforced
by code — a swapped or edited keyframe file would have passed silently.

Registry format (keyframes registry JSON):
    {"schema_version": "keyframe-registry-v1",
     "keyframes": {"KF_A1": {"file": "path", "sha256": "...",
                              "approval": "approved", "approved_by": "user",
                              "approved_at": "...", "scope": ["shot_id"]}}}

``file`` may be absolute or relative to the registry JSON itself.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from shortfilm.shot_extensions import _raw_shots, _text


def load_registry(path: str | Path) -> dict[str, Any]:
    registry = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(registry.get("keyframes"), dict):
        raise ValueError(f"{path}: expected a 'keyframes' object")
    return registry


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gate_errors(
    document: dict[str, Any],
    registry: dict[str, Any],
    registry_path: str | Path | None = None,
    *,
    require_first_frame: bool = True,
) -> list[str]:
    errors: list[str] = []
    keyframes = registry.get("keyframes") or {}
    base = Path(registry_path).resolve().parent if registry_path else None
    shots = _raw_shots(document)
    if not shots:
        return ["keyframe gate: document has no internal_shots/timeline"]
    for index, shot in enumerate(shots):
        label = _text(shot.get("shot_id")) or f"shot {index}"
        first_frame = shot.get("first_frame") or {}
        if not first_frame:
            if require_first_frame:
                errors.append(f"{label}: no first_frame — every shot needs an approved keyframe before paid rendering")
            continue
        keyframe_id = _text(first_frame.get("keyframe_id"))
        if not keyframe_id:
            errors.append(f"{label}: first_frame.keyframe_id is required")
            continue
        contract_approval = _text(first_frame.get("approval"))
        if contract_approval != "approved":
            errors.append(f"{label}: first_frame approval is '{contract_approval or 'missing'}' — user approval required before paid rendering")
            continue
        entry = keyframes.get(keyframe_id)
        if not isinstance(entry, dict):
            errors.append(f"{label}: keyframe {keyframe_id} not found in registry")
            continue
        if _text(entry.get("approval")) != "approved":
            errors.append(f"{label}: registry says keyframe {keyframe_id} is '{_text(entry.get('approval'))}'")
            continue
        file_ref = _text(entry.get("file"))
        if not file_ref:
            errors.append(f"{label}: registry entry for {keyframe_id} has no file")
            continue
        file_path = Path(file_ref)
        if not file_path.is_absolute() and base is not None:
            file_path = base / file_path
        if not file_path.is_file():
            errors.append(f"{label}: keyframe file missing: {file_path}")
            continue
        digest = _sha256(file_path)
        if digest != _text(entry.get("sha256")):
            errors.append(
                f"{label}: keyframe {keyframe_id} content changed since approval "
                f"(registry {_text(entry.get('sha256'))[:12]}…, on disk {digest[:12]}…) — re-approval required"
            )
    return errors
