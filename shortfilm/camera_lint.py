"""Deterministic camera-direction checks for MiniMax director contracts."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

MOVE_TERMS={
 "static":("static","locked","静止","固定"),
 "dolly_in":("push in","dolly in","推进","推近"),
 "dolly_out":("pull back","dolly out","拉远","后退"),
 "tracking":("track","follow","跟随","跟移"),
 "orbit":("orbit","arc","环绕","弧线","侧移"),
 "pan":("pan","摇摄","横摇"),
 "tilt":("tilt","俯仰","纵摇"),
 "crane":("crane","rise","lower","升降","上升","下降"),
}

@dataclass
class LintFinding:
    rule:str; severity:str; message:str; fix_hint:str
    def to_dict(self)->dict[str,str]: return asdict(self)

def _families(text:str)->set[str]:
    lower=text.lower()
    return {family for family,terms in MOVE_TERMS.items() if any(term in lower for term in terms)}

def lint_camera(document:dict[str,Any])->list[LintFinding]:
    out=[]; plan=document.get("camera_plan") or {}; timeline=document.get("timeline") or []
    primary=str(plan.get("primary_move") or "")
    actions=" ".join(str(x.get("camera_action") or "") for x in timeline if isinstance(x,dict))
    families=_families(actions)
    mapped={"slow_dolly_in":"dolly_in","arc":"orbit","crane_down":"crane","crane_up":"crane","handheld":"tracking"}.get(primary,primary)
    if primary!="static" and not str(plan.get("motivation") or "").strip():
        out.append(LintFinding("CAM01","error","moving camera lacks motivation","state what the movement reveals or follows"))
    if primary!="static" and mapped not in families:
        out.append(LintFinding("CAM02","error",f"primary move {primary} is not instantiated in timeline actions","use concrete bilingual movement verbs in at least one beat"))
    motion=families-{"static"}
    if primary=="static" and motion:
        out.append(LintFinding("CAM03","error","static plan conflicts with moving timeline","remove movement verbs or change primary_move"))
    if len(motion)>2:
        out.append(LintFinding("CAM04","warning",f"too many movement families: {sorted(motion)}","retain one dominant move and at most one motivated path change"))
    if int(plan.get("path_changes",0) or 0)>1:
        out.append(LintFinding("CAM05","error","more than one path change","simplify to one continuous path with one motivated change"))
    path=str(plan.get("path") or "").strip()
    cjk=sum('\u4e00'<=c<='\u9fff' for c in path)
    if len(path.split())<5 and cjk<8:
        out.append(LintFinding("CAM06","error","camera path is not physically specific","name start, direction, subject relation and endpoint"))
    if timeline:
        final=" ".join(str((timeline[-1] or {}).get(k,"") or "") for k in ("camera_action","subject_action","end_state")).lower()
        if not any(x in final for x in ("stop","settle","stable","deceler","停止","稳定","减速")):
            out.append(LintFinding("CAM07","error","final beat does not settle for edit","decelerate camera and subject into the declared hold"))
    return out
