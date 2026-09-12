"""Deterministic camera checks for legacy continuous and script-first multi-shot contracts."""
from __future__ import annotations
from dataclasses import dataclass,asdict
from typing import Any

MOVE_TERMS={
 "static":("static","locked","静止","固定"),
 "dolly_in":("push in","push-in","dolly in","dolly-in","move straight forward","forward dolly","推进","推近"),
 "dolly_out":("pull back","pull straight back","move straight backward","dolly out","dolly-out","拉远","后退"),
 "tracking":("track","follow","跟随","跟移"), "orbit":("orbit","arc","环绕","弧线","侧移"),
 "pan":("pan","摇摄","横摇"), "tilt":("tilt","俯仰","纵摇"), "crane":("crane","rise","lower","升降","上升","下降"),
}

@dataclass
class LintFinding:
    rule:str; severity:str; message:str; fix_hint:str
    def to_dict(self)->dict[str,str]: return asdict(self)

def _families(text:str)->set[str]:
    lower=text.lower(); return {family for family,terms in MOVE_TERMS.items() if any(term in lower for term in terms)}

def _lint_one(plan:dict[str,Any],actions:str,final_text:str,prefix:str="")->list[LintFinding]:
    out=[]; primary=str(plan.get("primary_move") or ""); families=_families(actions)
    mapped={"slow_dolly_in":"dolly_in","arc":"orbit","crane_down":"crane","crane_up":"crane","handheld":"tracking"}.get(primary,primary)
    def add(rule,severity,message,hint): out.append(LintFinding(rule,severity,prefix+message,hint))
    if primary!="static" and not str(plan.get("motivation") or "").strip(): add("CAM01","error","moving camera lacks motivation","state what the movement reveals or follows")
    if primary!="static" and mapped not in families: add("CAM02","error",f"primary move {primary} is not instantiated in camera action","use a concrete movement verb inside this shot")
    motion=families-{"static"}
    if primary=="static" and motion: add("CAM03","error","static plan conflicts with moving camera action","remove movement verbs or change primary_move")
    if len(motion)>2: add("CAM04","warning",f"too many movement families inside one shot: {sorted(motion)}","keep one dominant move per internal shot; put other moves after an explicit cut")
    if int(plan.get("path_changes",0) or 0)>1: add("CAM05","error","more than one path change inside one shot","simplify this shot or split at a motivated cut")
    path=str(plan.get("path") or "").strip(); cjk=sum('\u4e00'<=c<='\u9fff' for c in path)
    if len(path.split())<5 and cjk<8: add("CAM06","error","camera path is not physically specific","name start, direction, subject relation and endpoint")
    if not any(x in final_text.lower() for x in ("stop","settle","stable","deceler","cut","match","exit","停止","稳定","减速","切")):
        add("CAM07","error","shot exit is not declared","stop/settle for a hold or exit on a declared cut/match action")
    return out

def lint_camera(document:dict[str,Any])->list[LintFinding]:
    shots=document.get("internal_shots") or []
    if shots:
        out=[]
        for i,shot in enumerate(shots):
            plan=shot.get("camera_plan") or {}; actions=str(shot.get("camera_action") or "")
            final=" ".join(str(shot.get(k,"") or "") for k in ("camera_action","subject_action","end_state"))
            out.extend(_lint_one(plan,actions,final,prefix=f"internal shot {i} ({shot.get('shot_id','unnamed')}): "))
        return out
    plan=document.get("camera_plan") or {}; timeline=document.get("timeline") or []
    actions=" ".join(str(x.get("camera_action") or "") for x in timeline if isinstance(x,dict))
    final=" ".join(str((timeline[-1] or {}).get(k,"") or "") for k in ("camera_action","subject_action","end_state")) if timeline else ""
    return _lint_one(plan,actions,final)
