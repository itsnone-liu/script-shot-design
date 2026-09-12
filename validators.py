"""Pure deterministic story/package validators. No LLM imports."""
from __future__ import annotations
import re
from typing import Any

BEAT_FIELDS = ("state_in", "visible_event", "character_choice", "state_out", "causal_hook")

def validate_package(package: dict[str, Any], brief: dict[str, Any]) -> list[dict[str, Any]]:
    issues=[]
    beat_doc=package.get("beat_sheet") or {}
    beats=beat_doc.get("beats", beat_doc) if isinstance(beat_doc, dict) else beat_doc
    if not isinstance(beats, list): beats=[]
    if len(beats)<4: issues.append({"severity":"blocker","code":"too_few_beats","message":"at least four beats required"})
    for i,b in enumerate(beats):
        for f in BEAT_FIELDS:
            if not str(b.get(f, "")).strip(): issues.append({"severity":"blocker","code":"missing_beat_field","beat":i,"field":f})
    scene_doc=package.get("scene_cards") or {}
    scenes=scene_doc.get("scenes", scene_doc) if isinstance(scene_doc, dict) else scene_doc
    if not isinstance(scenes, list): scenes=[]
    beat_ids={b.get("id") for b in beats if isinstance(b, dict)}
    for scene in scenes:
        if scene.get("beat_id") not in beat_ids: issues.append({"severity":"blocker","code":"scene_beat_reference","scene":scene.get("id")})
    duration=float(brief.get("duration_sec",0) or 0)
    scene_total=sum(float(s.get("est_duration_sec",0) or 0) for s in scenes)
    if duration and scene_total and abs(scene_total-duration)>0.5: issues.append({"severity":"warning","code":"duration_mismatch","expected":duration,"actual":scene_total})
    script=str(package.get("script_markdown", ""))
    if not script.strip(): issues.append({"severity":"blocker","code":"missing_script"})
    if re.search(r"突然成功|一键完成|喝完就成功|灵感爆发", script): issues.append({"severity":"blocker","code":"sudden_success"})
    if len(re.findall(r"喝|饮用|拿起|产品特写|展示产品", script))>2: issues.append({"severity":"warning","code":"repeated_product_action"})
    if any(x in script.lower() for x in ("nsfw", "explicit sexual", "pornographic")): issues.append({"severity":"blocker","code":"nsfw_advisor_only"})
    return issues

def status(issues): return "block" if any(x["severity"]=="blocker" for x in issues) else "pass"
