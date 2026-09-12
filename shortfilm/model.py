"""Minimal, dependency-free project model and validation for the 30s MVP."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
import re
from typing import Any


SHOT_SIZES = {"extreme_wide", "wide", "medium", "medium_close_up", "close_up", "extreme_close_up"}
CAMERA_MOVES = {"static", "pan", "tilt", "dolly_in", "slow_dolly_in", "dolly_out", "tracking", "orbit", "handheld"}
MOVEMENT_INTENTS = {"establish", "reveal", "follow", "emphasize", "transition", "energize", "settle", "none"}
MOVEMENT_SPEEDS = {"very_slow", "slow", "medium", "fast", "very_fast"}
GENERATION_WORKFLOWS = {"pending", "rh_video", "post_composite"}


@dataclass
class Shot:
    shot_id: str
    scene_id: str
    story_beat: str
    duration: float
    shot_size: str
    attention_subject: str = "product"
    product_visibility: str = "visible"
    angle: str = "eye_level"
    composition: str = "rule_of_thirds"
    camera_move: str = "static"
    movement_intent: str = "none"
    movement_speed: str = "slow"
    start_framing: str = "initial composition"
    end_framing: str = "final composition"
    stabilization: str = "tripod"
    screen_direction: str = "consistent"
    transition_to_next: str = "cut"
    subject_action: str = ""
    # Optional model-ready prompt.  When present the renderer sends this text
    # verbatim instead of rebuilding a terse prompt from shot metadata.  This
    # is useful for long-form MiniMax segments with an internal shot timeline.
    generation_prompt: str = ""
    gaze: str = "camera"
    lighting: str = ""
    continuity_in: str = ""
    continuity_out: str = ""
    dialogue_or_vo: str = ""
    sound: str = ""
    reference_assets: list[str] = field(default_factory=list)
    generation_workflow: str = "pending"
    acceptance_tests: list[str] = field(default_factory=list)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.shot_id or not self.scene_id or not self.story_beat:
            errors.append(f"{self.shot_id or '<unknown>'}: missing identity/story beat")
        if self.duration <= 0 or self.duration > 15:
            errors.append(f"{self.shot_id}: duration must be in (0, 15]")
        if self.shot_size not in SHOT_SIZES:
            errors.append(f"{self.shot_id}: unsupported shot_size={self.shot_size}")
        if self.camera_move not in CAMERA_MOVES:
            errors.append(f"{self.shot_id}: unsupported camera_move={self.camera_move}")
        if self.movement_intent not in MOVEMENT_INTENTS:
            errors.append(f"{self.shot_id}: unsupported movement_intent={self.movement_intent}")
        if self.movement_speed not in MOVEMENT_SPEEDS:
            errors.append(f"{self.shot_id}: unsupported movement_speed={self.movement_speed}")
        if self.generation_workflow not in GENERATION_WORKFLOWS:
            errors.append(
                f"{self.shot_id}: unsupported generation_workflow={self.generation_workflow}"
            )
        if self.camera_move != "static" and self.movement_intent == "none":
            errors.append(f"{self.shot_id}: moving camera needs a movement_intent")
        if not self.start_framing or not self.end_framing:
            errors.append(f"{self.shot_id}: start_framing and end_framing are required")
        if not self.continuity_out:
            errors.append(f"{self.shot_id}: continuity_out is required")
        if not self.acceptance_tests:
            errors.append(f"{self.shot_id}: acceptance_tests is required")
        if self.generation_prompt:
            if len(self.generation_prompt) > 7000:
                errors.append(
                    f"{self.shot_id}: generation_prompt exceeds MiniMax 7000-character limit"
                )
            prompt_lower = self.generation_prompt.lower()
            for section in ("internal shot timeline", "never show"):
                if section not in prompt_lower:
                    errors.append(
                        f"{self.shot_id}: generation_prompt missing '{section}' section"
                    )
            if "continuity" not in prompt_lower and "location and cast lock" not in prompt_lower:
                errors.append(
                    f"{self.shot_id}: generation_prompt missing continuity lock section"
                )
            if not re.search(r"final\s+\d+(?:\.\d+)?\s*seconds?", prompt_lower):
                errors.append(
                    f"{self.shot_id}: generation_prompt must define a final hold/interface state"
                )
        return errors


@dataclass
class AdProject:
    project_id: str
    title: str
    duration_target: float = 30.0
    aspect_ratio: str = "9:16"
    audience: str = ""
    product: str = ""
    core_message: str = ""
    visual_style: str = ""
    story_template: str = "deadline_breakthrough_v1"
    shots: list[Shot] = field(default_factory=list)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.duration_target != 30:
            errors.append("MVP target duration must be exactly 30 seconds")
        if self.aspect_ratio != "9:16":
            errors.append("MVP aspect_ratio must be 9:16")
        if not self.product or not self.core_message:
            errors.append("product and core_message are required")
        if not self.shots:
            errors.append("at least one shot is required")
        errors.extend(error for shot in self.shots for error in shot.validate())
        total = sum(shot.duration for shot in self.shots)
        if abs(total - self.duration_target) > 0.25:
            errors.append(f"shot durations total {total:.2f}s, target is {self.duration_target:.2f}s")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
