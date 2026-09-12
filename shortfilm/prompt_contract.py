"""Structured director contract and deterministic MiniMax prompt compiler."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

APPROVAL_STATES = {"pending", "revise", "approved", "rejected"}
SHOT_SIZES = {"extreme_wide", "wide", "medium", "medium_close_up", "close_up", "extreme_close_up"}
CAMERA_MOVES = {"static", "pan", "tilt", "dolly_in", "slow_dolly_in", "dolly_out", "tracking", "orbit", "handheld", "crane_down", "crane_up", "arc"}


def _text(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(x).strip() for x in value if str(x).strip())
    return str(value or "").strip()


@dataclass
class ScriptApproval:
    status: str = "pending"
    script_version: str = ""
    reviewed_by: str = ""
    reviewed_at: str = ""
    feedback: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "ScriptApproval":
        value = value or {}
        return cls(status=_text(value.get("status")) or "pending",
                   script_version=_text(value.get("script_version")),
                   reviewed_by=_text(value.get("reviewed_by")),
                   reviewed_at=_text(value.get("reviewed_at")),
                   feedback=list(value.get("feedback") or []))

    def validate(self, *, require_approved: bool = True) -> list[str]:
        errors=[]
        if self.status not in APPROVAL_STATES: errors.append(f"unsupported approval status={self.status}")
        if require_approved and self.status != "approved": errors.append("user script approval is required before shot export")
        if self.status == "approved" and not self.script_version: errors.append("approved script_version is required")
        if self.status == "approved" and not self.reviewed_by: errors.append("approved reviewed_by is required")
        if self.status == "revise" and not self.feedback: errors.append("revision feedback is required")
        return errors


@dataclass
class PromptBible:
    subject_lock: str
    environment_lock: str
    material_lock: str
    lighting_lock: str
    palette_lock: str
    lens_texture: str
    screen_direction: str
    audio_policy: str = "environment sound only"
    never_show: list[str] = field(default_factory=lambda: ["readable text", "logo", "watermark", "UI", "geometric placeholders"])

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "PromptBible":
        return cls(subject_lock=_text(value.get("subject_lock")), environment_lock=_text(value.get("environment_lock")),
                   material_lock=_text(value.get("material_lock")), lighting_lock=_text(value.get("lighting_lock")),
                   palette_lock=_text(value.get("palette_lock")), lens_texture=_text(value.get("lens_texture")),
                   screen_direction=_text(value.get("screen_direction")), audio_policy=_text(value.get("audio_policy")) or "environment sound only",
                   never_show=list(value.get("never_show") or []))

    def validate(self) -> list[str]:
        errors=[]
        for name in ("subject_lock","environment_lock","material_lock","lighting_lock","palette_lock","lens_texture","screen_direction"):
            if not _text(getattr(self,name)): errors.append(f"prompt_bible missing {name}")
        if len(self.never_show)<3: errors.append("prompt_bible never_show needs at least three concrete exclusions")
        return errors


@dataclass
class TimelineBeat:
    start: float
    end: float
    shot_size: str
    visual_state: str
    subject_action: str
    camera_action: str
    focus: str
    lighting_state: str
    end_state: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TimelineBeat": return cls(**value)


@dataclass
class CameraPlan:
    motivation: str
    start_position: str
    path: str
    speed_curve: str
    focus_transition: str
    end_position: str
    axis_lock: str
    stop_condition: str
    primary_move: str
    path_changes: int = 0

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CameraPlan": return cls(**value)

    def validate(self) -> list[str]:
        errors=[]
        for name in ("motivation","start_position","path","speed_curve","focus_transition","end_position","axis_lock","stop_condition"):
            if not _text(getattr(self,name)): errors.append(f"camera_plan missing {name}")
        if self.primary_move not in CAMERA_MOVES: errors.append(f"unsupported primary_move={self.primary_move}")
        if self.path_changes > 1: errors.append("camera_plan allows at most one motivated path change")
        if self.primary_move != "static" and len(self.path.split()) < 3: errors.append("moving camera path is underspecified")
        return errors


def validate_director_contract(document: dict[str, Any], *, require_approval: bool = True) -> list[str]:
    errors=[]
    approval=ScriptApproval.from_dict(document.get("user_script_review"))
    errors.extend(approval.validate(require_approved=require_approval))
    bible=PromptBible.from_dict(document.get("prompt_bible") or {})
    errors.extend(bible.validate())
    duration=float(document.get("duration",0) or 0)
    beats=[TimelineBeat.from_dict(x) for x in document.get("timeline",[]) if isinstance(x,dict)]
    if duration < 4 or duration > 15: errors.append("segment duration must be in [4, 15] seconds")
    if not beats: errors.append("internal timeline is required"); return errors
    if len(beats)<3 or len(beats)>6: errors.append("internal timeline needs 3-6 beats per segment")
    cursor=0.0
    for index,beat in enumerate(beats):
        if abs(beat.start-cursor)>0.01: errors.append(f"timeline beat {index} must start at {cursor:g}")
        if beat.end <= beat.start: errors.append(f"timeline beat {index} has invalid duration")
        if beat.shot_size not in SHOT_SIZES: errors.append(f"timeline beat {index} unsupported shot_size={beat.shot_size}")
        for name in ("visual_state","subject_action","camera_action","focus","lighting_state","end_state"):
            if not _text(getattr(beat,name)): errors.append(f"timeline beat {index} missing {name}")
        cursor=beat.end
    if abs(cursor-duration)>0.01: errors.append(f"timeline ends at {cursor:g}, duration is {duration:g}")
    plan=CameraPlan.from_dict(document.get("camera_plan") or {})
    errors.extend(plan.validate())
    if not _text(document.get("main_visual_task")): errors.append("one main_visual_task is required")
    if not _text(document.get("first_frame")) or not _text(document.get("last_frame")): errors.append("first_frame and last_frame are required")
    hold=float(document.get("final_hold_seconds",0) or 0)
    if hold<1: errors.append("final hold must be at least 1 second")
    if hold>=duration and duration: errors.append("final hold must be shorter than segment duration")
    return errors


def compile_minimax_prompt(document: dict[str, Any]) -> str:
    errors=validate_director_contract(document)
    if errors: raise ValueError("director contract invalid: " + "; ".join(errors))
    bible=PromptBible.from_dict(document["prompt_bible"])
    plan=CameraPlan.from_dict(document["camera_plan"])
    beats=[TimelineBeat.from_dict(x) for x in document["timeline"]]
    timeline="\n".join(
        f"{b.start:g}-{b.end:g}s | {b.shot_size} | visual state: {b.visual_state} | subject action: {b.subject_action} | camera: {b.camera_action} | focus: {b.focus} | lighting: {b.lighting_state} | end state: {b.end_state}"
        for b in beats)
    prompt=f"""MAIN VISUAL TASK\n{_text(document['main_visual_task'])}\n\nPROMPT BIBLE / CONTINUITY LOCK\nSubject: {bible.subject_lock}\nEnvironment: {bible.environment_lock}\nMaterials: {bible.material_lock}\nLighting: {bible.lighting_lock}\nPalette: {bible.palette_lock}\nLens and texture: {bible.lens_texture}\nScreen direction: {bible.screen_direction}\nAudio policy: {bible.audio_policy}\n\nINTERNAL SHOT TIMELINE\n{timeline}\n\nCAMERA PATH\nMotivation: {plan.motivation}\nStart position: {plan.start_position}\nPrimary move: {plan.primary_move}\nPhysical path: {plan.path}\nSpeed curve: {plan.speed_curve}\nFocus transition: {plan.focus_transition}\nEnd position: {plan.end_position}\nAxis lock: {plan.axis_lock}\nStop condition: {plan.stop_condition}\n\nFIRST FRAME\n{_text(document['first_frame'])}\n\nLAST FRAME\n{_text(document['last_frame'])}\n\nFINAL {float(document['final_hold_seconds']):g} SECONDS HOLD\nAll subject and camera movement decelerates to a stable, editable end state.\n\nNEVER SHOW\n{_text(bible.never_show)}"""
    if len(prompt)>7000: raise ValueError(f"compiled MiniMax prompt exceeds 7000 characters: {len(prompt)}")
    return prompt
