"""Script-first director contracts and deterministic MiniMax prompt compiler.

A generation segment is a 4–15 second technical container, not necessarily one
shot. New contracts use ``internal_shots`` with explicit cuts and a camera plan
per internal shot. Legacy ``timeline`` + top-level ``camera_plan`` remains
supported for already-approved continuous-shot experiments.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

APPROVAL_STATES={"pending","revise","approved","rejected"}
SHOT_SIZES={"extreme_wide","wide","medium","medium_close_up","close_up","extreme_close_up"}
CAMERA_MOVES={"static","pan","tilt","dolly_in","slow_dolly_in","dolly_out","tracking","orbit","handheld","crane_down","crane_up","arc"}
CUT_TYPES={"opening","continuous","hard_cut","match_cut","smash_cut","whip_cut","dissolve"}


def _text(value:Any)->str:
    if isinstance(value,list): return ", ".join(str(x).strip() for x in value if str(x).strip())
    return str(value or "").strip()


@dataclass
class ScriptApproval:
    status:str="pending"; script_version:str=""; reviewed_by:str=""; reviewed_at:str=""; feedback:list[str]=field(default_factory=list)
    @classmethod
    def from_dict(cls,value:dict[str,Any]|None)->"ScriptApproval":
        value=value or {}; return cls(status=_text(value.get("status")) or "pending",script_version=_text(value.get("script_version")),reviewed_by=_text(value.get("reviewed_by")),reviewed_at=_text(value.get("reviewed_at")),feedback=list(value.get("feedback") or []))
    def validate(self,*,require_approved:bool=True)->list[str]:
        errors=[]
        if self.status not in APPROVAL_STATES: errors.append(f"unsupported approval status={self.status}")
        if require_approved and self.status!="approved": errors.append("user script approval is required before shot export")
        if self.status=="approved" and not self.script_version: errors.append("approved script_version is required")
        if self.status=="approved" and not self.reviewed_by: errors.append("approved reviewed_by is required")
        if self.status=="revise" and not self.feedback: errors.append("revision feedback is required")
        return errors


@dataclass
class PromptBible:
    subject_lock:str; environment_lock:str; material_lock:str; lighting_lock:str; palette_lock:str; lens_texture:str; screen_direction:str
    audio_policy:str="environment sound only"; never_show:list[str]=field(default_factory=lambda:["readable text","logo","watermark","UI","geometric placeholders"])
    @classmethod
    def from_dict(cls,value:dict[str,Any])->"PromptBible":
        return cls(subject_lock=_text(value.get("subject_lock")),environment_lock=_text(value.get("environment_lock")),material_lock=_text(value.get("material_lock")),lighting_lock=_text(value.get("lighting_lock")),palette_lock=_text(value.get("palette_lock")),lens_texture=_text(value.get("lens_texture")),screen_direction=_text(value.get("screen_direction")),audio_policy=_text(value.get("audio_policy")) or "environment sound only",never_show=list(value.get("never_show") or []))
    def validate(self)->list[str]:
        errors=[]
        for name in ("subject_lock","environment_lock","material_lock","lighting_lock","palette_lock","lens_texture","screen_direction"):
            if not _text(getattr(self,name)): errors.append(f"prompt_bible missing {name}")
        if len(self.never_show)<3: errors.append("prompt_bible never_show needs at least three concrete exclusions")
        return errors


@dataclass
class TimelineBeat:
    start:float; end:float; shot_size:str; visual_state:str; subject_action:str; camera_action:str; focus:str; lighting_state:str; end_state:str
    @classmethod
    def from_dict(cls,value:dict[str,Any])->"TimelineBeat": return cls(**value)


@dataclass
class CameraPlan:
    motivation:str; start_position:str; path:str; speed_curve:str; focus_transition:str; end_position:str; axis_lock:str; stop_condition:str; primary_move:str; path_changes:int=0
    @classmethod
    def from_dict(cls,value:dict[str,Any])->"CameraPlan": return cls(**value)
    def validate(self)->list[str]:
        errors=[]
        for name in ("motivation","start_position","path","speed_curve","focus_transition","end_position","axis_lock","stop_condition"):
            if not _text(getattr(self,name)): errors.append(f"camera_plan missing {name}")
        if self.primary_move not in CAMERA_MOVES: errors.append(f"unsupported primary_move={self.primary_move}")
        if self.path_changes>1: errors.append("camera_plan allows at most one motivated path change")
        if self.primary_move!="static" and len(self.path.split())<3: errors.append("moving camera path is underspecified")
        return errors


@dataclass
class InternalShot:
    shot_id:str; start:float; end:float; transition_in:str; shot_size:str; visual_state:str; subject_action:str; camera_action:str; focus:str; lighting_state:str; end_state:str; camera_plan:CameraPlan
    @classmethod
    def from_dict(cls,value:dict[str,Any],index:int)->"InternalShot":
        return cls(shot_id=_text(value.get("shot_id")) or f"shot_{index+1}",start=float(value.get("start",0)),end=float(value.get("end",0)),transition_in=_text(value.get("transition_in")) or ("opening" if index==0 else "continuous"),shot_size=_text(value.get("shot_size")),visual_state=_text(value.get("visual_state")),subject_action=_text(value.get("subject_action")),camera_action=_text(value.get("camera_action")),focus=_text(value.get("focus")),lighting_state=_text(value.get("lighting_state")),end_state=_text(value.get("end_state")),camera_plan=CameraPlan.from_dict(value.get("camera_plan") or {}))


def _validate_time(items:list[Any],duration:float,label:str)->list[str]:
    errors=[]; cursor=0.0
    for index,item in enumerate(items):
        if abs(item.start-cursor)>0.01: errors.append(f"{label} {index} must start at {cursor:g}")
        if item.end<=item.start: errors.append(f"{label} {index} has invalid duration")
        cursor=item.end
    if abs(cursor-duration)>0.01: errors.append(f"{label} ends at {cursor:g}, duration is {duration:g}")
    return errors


def validate_director_contract(document:dict[str,Any],*,require_approval:bool=True)->list[str]:
    errors=[]
    errors.extend(ScriptApproval.from_dict(document.get("user_script_review")).validate(require_approved=require_approval))
    errors.extend(PromptBible.from_dict(document.get("prompt_bible") or {}).validate())
    duration=float(document.get("duration",0) or 0)
    if duration<4 or duration>15: errors.append("generation segment duration must be in [4, 15] seconds")
    multi=bool(document.get("internal_shots"))
    if multi:
        shots=[InternalShot.from_dict(x,i) for i,x in enumerate(document.get("internal_shots",[])) if isinstance(x,dict)]
        if not shots: errors.append("internal_shots are required")
        if len(shots)>8: errors.append("generation segment allows at most 8 internal shots")
        errors.extend(_validate_time(shots,duration,"internal shot"))
        for i,shot in enumerate(shots):
            if shot.transition_in not in CUT_TYPES: errors.append(f"internal shot {i} unsupported transition_in={shot.transition_in}")
            if i==0 and shot.transition_in!="opening": errors.append("first internal shot transition_in must be opening")
            if i>0 and shot.transition_in=="opening": errors.append(f"internal shot {i} cannot use opening transition")
            if shot.shot_size not in SHOT_SIZES: errors.append(f"internal shot {i} unsupported shot_size={shot.shot_size}")
            for name in ("visual_state","subject_action","camera_action","focus","lighting_state","end_state"):
                if not _text(getattr(shot,name)): errors.append(f"internal shot {i} missing {name}")
            errors.extend(f"internal shot {i}: {e}" for e in shot.camera_plan.validate())
    else:
        beats=[TimelineBeat.from_dict(x) for x in document.get("timeline",[]) if isinstance(x,dict)]
        if not beats: errors.append("timeline or internal_shots is required"); return errors
        if len(beats)<3 or len(beats)>6: errors.append("legacy timeline needs 3-6 beats per segment")
        errors.extend(_validate_time(beats,duration,"timeline beat"))
        for i,beat in enumerate(beats):
            if beat.shot_size not in SHOT_SIZES: errors.append(f"timeline beat {i} unsupported shot_size={beat.shot_size}")
            for name in ("visual_state","subject_action","camera_action","focus","lighting_state","end_state"):
                if not _text(getattr(beat,name)): errors.append(f"timeline beat {i} missing {name}")
        errors.extend(CameraPlan.from_dict(document.get("camera_plan") or {}).validate())
    if not _text(document.get("main_visual_task")): errors.append("one main_visual_task is required")
    if not _text(document.get("first_frame")) or not _text(document.get("last_frame")): errors.append("first_frame and last_frame are required")
    hold=float(document.get("final_hold_seconds",0) or 0)
    if multi:
        edit_role=_text(document.get("edit_role")) or "middle"
        if hold<0: errors.append("final hold cannot be negative")
        if edit_role=="final" and hold<1: errors.append("final generation segment needs at least 1 second hold")
    elif hold<1: errors.append("legacy continuous segment final hold must be at least 1 second")
    if hold>=duration and duration: errors.append("final hold must be shorter than segment duration")
    return errors


def _bible_text(bible:PromptBible)->str:
    return f"Subject: {bible.subject_lock}\nEnvironment: {bible.environment_lock}\nMaterials: {bible.material_lock}\nLighting: {bible.lighting_lock}\nPalette: {bible.palette_lock}\nLens and texture: {bible.lens_texture}\nScreen direction: {bible.screen_direction}\nAudio policy: {bible.audio_policy}"


def compile_minimax_prompt(document:dict[str,Any])->str:
    errors=validate_director_contract(document)
    if errors: raise ValueError("director contract invalid: "+"; ".join(errors))
    bible=PromptBible.from_dict(document["prompt_bible"])
    if document.get("internal_shots"):
        shots=[InternalShot.from_dict(x,i) for i,x in enumerate(document["internal_shots"])]
        blocks=[]
        for i,s in enumerate(shots,1):
            p=s.camera_plan
            raw=document["internal_shots"][i-1]
            design=raw.get("cinematic_design") or {}
            audience=design.get("audience_knowledge") or {}
            blocking=design.get("blocking_map") or {}
            performance=design.get("performance_detail") or {}
            light=design.get("light_motivation") or {}
            budget=design.get("event_budget") or {}
            director_note=""
            if design:
                director_note=(
                    f"\nNarrative job: {_text(design.get('narrative_job'))}"
                    f"\nAudience information: knows={_text(audience.get('knows'))}; withheld={_text(audience.get('does_not_know'))}; question={_text(audience.get('question'))}"
                    f"\nComposition: {_text(design.get('composition_logic'))}; foreground={_text(design.get('foreground'))}; midground={_text(design.get('midground'))}; background={_text(design.get('background'))}"
                    f"\nBlocking map: subject={_text(blocking.get('subject_position'))}; movement={_text(blocking.get('movement_path'))}; camera={_text(blocking.get('camera_position'))}; screen direction={_text(blocking.get('screen_direction'))}"
                    f"\nPerformance: micro-action={_text(performance.get('micro_action'))}; reaction order={_text(performance.get('reaction_order'))}"
                    f"\nMotivated light: source={_text(light.get('source'))}; direction={_text(light.get('direction'))}; color temperature={_text(light.get('color_temperature'))}"
                    f"\nEvent density: at most {_text(budget.get('max_concurrent_events'))} concurrent visual events; timed events={_text(budget.get('timed_events'))}"
                )
            blocks.append(f"SHOT {i} [{s.shot_id}] {s.start:g}-{s.end:g}s | CUT IN: {s.transition_in.upper()}\nFraming: {s.shot_size}\nVisual state: {s.visual_state}\nSubject action: {s.subject_action}\nCamera action: {s.camera_action}\nShot camera plan: {p.primary_move}; path={p.path}; speed={p.speed_curve}; focus={p.focus_transition}; axis={p.axis_lock}; stop={p.stop_condition}\nLighting: {s.lighting_state}\nExit state: {s.end_state}{director_note}")
        hold=float(document.get("final_hold_seconds",0) or 0)
        exit_rule=(f"Hold the final composition still for {hold:g} seconds." if hold>0 else "Exit on the declared action or visual state for the edit; do not insert an artificial pause.")
        prompt=f"""MAIN VISUAL TASK\n{_text(document['main_visual_task'])}\n\nPROMPT BIBLE / CONTINUITY LOCK\n{_bible_text(bible)}\n\nINTERNAL EDIT / SHOT LIST\n{chr(10).join(blocks)}\n\nEDITING AND PERFORMANCE RULE\nHonor every explicit cut and its timing. Each internal shot has its own information job and camera move; do not blend different shots into one continuous camera path. Preserve subject, material, physically motivated light and screen direction across cuts. Execute written micro-actions and reaction order; do not make people move in perfect synchronization. Never exceed the declared concurrent visual-event budget. Use restrained human breathing only where requested; do not add default frictionless gimbal motion.\n\nFIRST FRAME\n{_text(document['first_frame'])}\n\nLAST FRAME\n{_text(document['last_frame'])}\n\nSEGMENT EXIT\n{exit_rule}\n\nNEVER SHOW\n{_text(bible.never_show)}"""
    else:
        plan=CameraPlan.from_dict(document["camera_plan"]); beats=[TimelineBeat.from_dict(x) for x in document["timeline"]]
        timeline="\n".join(f"{b.start:g}-{b.end:g}s | {b.shot_size} | visual state: {b.visual_state} | subject action: {b.subject_action} | camera: {b.camera_action} | focus: {b.focus} | lighting: {b.lighting_state} | end state: {b.end_state}" for b in beats)
        prompt=f"""MAIN VISUAL TASK\n{_text(document['main_visual_task'])}\n\nPROMPT BIBLE / CONTINUITY LOCK\n{_bible_text(bible)}\n\nINTERNAL SHOT TIMELINE\n{timeline}\n\nCAMERA PATH\nMotivation: {plan.motivation}\nStart position: {plan.start_position}\nPrimary move: {plan.primary_move}\nPhysical path: {plan.path}\nSpeed curve: {plan.speed_curve}\nFocus transition: {plan.focus_transition}\nEnd position: {plan.end_position}\nAxis lock: {plan.axis_lock}\nStop condition: {plan.stop_condition}\n\nFIRST FRAME\n{_text(document['first_frame'])}\n\nLAST FRAME\n{_text(document['last_frame'])}\n\nFINAL {float(document['final_hold_seconds']):g} SECONDS HOLD\nAll subject and camera movement decelerates to a stable, editable end state.\n\nNEVER SHOW\n{_text(bible.never_show)}"""
    if len(prompt)>7000: raise ValueError(f"compiled MiniMax prompt exceeds 7000 characters: {len(prompt)}")
    return prompt
