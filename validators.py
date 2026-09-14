"""Pure deterministic story/package validators. No LLM imports."""
from __future__ import annotations
import re
from typing import Any

from shortfilm.creative_quality import (
    validate_beat_design,
    validate_cinematic_scene_design,
    validate_creative_strategy,
    validate_story_design,
)

BEAT_FIELDS = ("state_in", "visible_event", "character_choice", "state_out", "causal_hook")

def validate_package(package: dict[str, Any], brief: dict[str, Any]) -> list[dict[str, Any]]:
    issues=[]
    beat_doc=package.get("beat_sheet") or {}
    beats=beat_doc.get("beats", beat_doc) if isinstance(beat_doc, dict) else beat_doc
    if not isinstance(beats, list): beats=[]
    if len(beats)<4: issues.append({"severity":"blocker","code":"too_few_beats","message":"at least four beats required"})
    for i,b in enumerate(beats):
        if not isinstance(b, dict):
            issues.append({"severity":"blocker","code":"invalid_beat","beat":i})
            continue
        for f in BEAT_FIELDS:
            if not str(b.get(f, "")).strip(): issues.append({"severity":"blocker","code":"missing_beat_field","beat":i,"field":f})
    scene_doc=package.get("scene_cards") or {}
    scenes=scene_doc.get("scenes", scene_doc) if isinstance(scene_doc, dict) else scene_doc
    if not isinstance(scenes, list): scenes=[]
    beat_ids={b.get("id") for b in beats if isinstance(b, dict)}
    for scene in scenes:
        if not isinstance(scene, dict):
            issues.append({"severity":"blocker","code":"invalid_scene"})
            continue
        if scene.get("beat_id") not in beat_ids and scene.get("beat_id") is not None: issues.append({"severity":"blocker","code":"scene_beat_reference","scene":scene.get("id")})
    duration=float(brief.get("duration_sec",0) or 0)
    scene_total=sum(float(s.get("est_duration_sec",0) or 0) for s in scenes)
    if duration and scene_total and abs(scene_total-duration)>0.5: issues.append({"severity":"warning","code":"duration_mismatch","expected":duration,"actual":scene_total})
    script_value=package.get("script_markdown", "")
    script = script_value.get("markdown", "") if isinstance(script_value, dict) else str(script_value)
    if not script.strip(): issues.append({"severity":"blocker","code":"missing_script"})
    if re.search(r"突然成功|一键完成|喝完就成功|灵感爆发", script): issues.append({"severity":"blocker","code":"sudden_success"})
    if len(re.findall(r"喝|饮用|拿起|产品特写|展示产品", script))>2: issues.append({"severity":"warning","code":"repeated_product_action"})
    if any(x in script.lower() for x in ("nsfw", "explicit sexual", "pornographic")): issues.append({"severity":"blocker","code":"nsfw_advisor_only"})
    issues.extend(validate_creative_strategy(package.get("concept_candidates") or {}))
    issues.extend(validate_story_design(package.get("story_statement") or {}))
    issues.extend(validate_beat_design(package.get("beat_sheet") or {}))
    issues.extend(validate_cinematic_scene_design(package.get("scene_cards") or {}))
    return issues

def validate_visual_design(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Gate product-visual concepts before any image/video generation.

    A negative prompt saying 'no blocks' is not sufficient: the positive design
    must specify recognizable material, a physical action, and a before/after state.
    """
    issues=[]
    forbidden=("方块","几何体","几何块","抽象图形","简单图形","随机粒子","漂浮粒子","视觉化答案","创意雏形","抽象形态","高级感","abstract shape","random geometry","floating particles")
    required_material=("咖啡","豆","液体","水","粉","油脂","冰","冷凝","玻璃","容器","泡沫")
    required_action=("落入","滴落","滴下","下沉","浸泡","吸水","渗透","湿润","溶解","萃取","流动","旋涡","凝结","破裂","注入","研磨","扩散","聚结","汇聚","融化","转化")
    concepts=document.get("concepts",[]) if isinstance(document,dict) else []
    if not isinstance(concepts,list) or len(concepts)<3:
        issues.append({"severity":"blocker","code":"too_few_visual_concepts"})
    for i,concept in enumerate(concepts):
        if not isinstance(concept,dict):
            issues.append({"severity":"blocker","code":"invalid_visual_concept","concept":i}); continue
        positive=" ".join(str(concept.get(k,"")) for k in ("product_property","transformation_chain","physical_causality","minimax_visual_fit"))
        lower=positive.lower()
        hits=[x for x in forbidden if x.lower() in lower]
        if hits: issues.append({"severity":"blocker","code":"abstract_visual_placeholder","concept":concept.get("id",i),"terms":hits})
        if not any(x in positive for x in required_material): issues.append({"severity":"blocker","code":"missing_concrete_material","concept":concept.get("id",i)})
        if not any(x in positive for x in required_action): issues.append({"severity":"blocker","code":"missing_physical_action","concept":concept.get("id",i)})
        for field in ("product_property","transformation_chain","physical_causality","anti_block_design","minimax_visual_fit","risk_flags"):
            if not concept.get(field): issues.append({"severity":"blocker","code":"missing_visual_contract_field","concept":concept.get("id",i),"field":field})
    selected=document.get("selected_concept",{}) if isinstance(document,dict) else {}
    selected_text=" ".join(str(selected.get(k,"")) for k in ("name","reason")) if isinstance(selected,dict) else str(selected)
    if any(x.lower() in selected_text.lower() for x in forbidden):
        issues.append({"severity":"blocker","code":"selected_concept_abstract_placeholder"})
    script=document.get("script",{}) if isinstance(document,dict) else {}
    if not isinstance(script,dict): issues.append({"severity":"blocker","code":"missing_visual_script"}); return issues
    for part,section in script.items():
        if not isinstance(section,dict): continue
        text=" ".join(str(section.get(k,"")) for k in ("timeline_0_3","timeline_3_7","timeline_7_11","timeline_11_15","camera_path","first_frame","last_frame","transition_to_next"))
        prompt_text=str((document.get("prompts",{}) or {}).get(part,"")) if isinstance(document.get("prompts",{}),dict) else ""
        all_text=text+" "+prompt_text
        positive_prompt=re.split(r"禁止|不可出现|never show",prompt_text,flags=re.I)[0]
        positive_all=text+" "+positive_prompt
        hits=[x for x in forbidden if x.lower() in positive_all.lower()]
        if hits: issues.append({"severity":"blocker","code":"abstract_prompt_placeholder","part":part,"terms":hits})
        if not any(x in text for x in required_material): issues.append({"severity":"blocker","code":"script_lacks_material","part":part})
        if not any(x in text for x in required_action): issues.append({"severity":"blocker","code":"script_lacks_physical_action","part":part})
        if not section.get("first_frame") or not section.get("last_frame"): issues.append({"severity":"blocker","code":"missing_visual_endpoint","part":part})
        for field in ("timeline_0_3","timeline_3_7","timeline_7_11","timeline_11_15","camera_path","first_frame","last_frame"):
            if not str(section.get(field,"" )).strip(): issues.append({"severity":"blocker","code":"missing_visual_script_field","part":part,"field":field})
    prompts=document.get("prompts",{}) if isinstance(document,dict) else {}
    if not isinstance(prompts,dict):
        issues.append({"severity":"blocker","code":"missing_long_shot_prompts"})
    else:
        expected_parts=set(script.keys())
        prompt_parts={k[:-7] if k.endswith("_prompt") else k for k in prompts.keys()}
        if len(expected_parts)<2 or not expected_parts.issubset(prompt_parts):
            issues.append({"severity":"blocker","code":"prompt_script_part_mismatch","script_parts":sorted(expected_parts),"prompt_parts":sorted(prompt_parts)})
        for part in expected_parts:
            raw=prompts.get(part) or prompts.get(part+"_prompt") or ""
            prompt=str(raw)
            positive_prompt=re.split(r"禁止|不可出现|never show",prompt,flags=re.I)[0]
            hits=[x for x in forbidden if x.lower() in positive_prompt.lower()]
            if hits: issues.append({"severity":"blocker","code":"abstract_prompt_placeholder","part":part,"terms":hits})
            if not all(x in prompt for x in ("总时长","时间线","镜头路径","首帧","尾帧","禁止")):
                issues.append({"severity":"blocker","code":"incomplete_minimax_prompt","part":part})
    return issues

def status(issues): return "block" if any(x["severity"]=="blocker" for x in issues) else "pass"

def validate_document(document: dict[str, Any], schema_name: str) -> list[dict[str, Any]]:
    """Small dependency-free contract check used before stage handoff."""
    required = {
        "concept_candidates": ("candidates",), "story_statement": ("logline", "protagonist", "desire", "obstacle"),
        "beat_sheet": ("beats",), "scene_cards": ("scenes",), "script_markdown": ("markdown",), "reviews": ("reviews",),
    }.get(schema_name, ())
    issues = [{"severity":"blocker", "code":"missing_contract_field", "stage":schema_name, "field":field}
              for field in required if not document.get(field)]
    if schema_name == "concept_candidates" and document.get("candidates"):
        issues.extend(validate_creative_strategy(document))
    if schema_name == "story_statement" and document.get("logline"):
        issues.extend(validate_story_design(document))
    if schema_name == "beat_sheet" and document.get("beats"):
        issues.extend(validate_beat_design(document))
    if schema_name == "scene_cards" and document.get("scenes"):
        issues.extend(validate_cinematic_scene_design(document))
    return issues
