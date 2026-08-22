"""mapper.py —— 语义页 -> 模板参考页选择与槽位映射（移植 native_presentation_bridge）。

差异（有意）：
- revise_page 不再自动重选参考页：source_slide 由用户在 UI 指定或沿用当前页；
  instruction 只驱动槽位文字重排（lab 单页修订契约：本地不猜内容，云端只出替换集）。
"""
from __future__ import annotations

import json

from . import lab_client, llm


def _preferred_kinds(slide: dict) -> list[str]:
    slide_type = str(slide.get("type") or "content")
    visual_type = str((slide.get("visual") or {}).get("type") or "none")
    if slide_type == "title":
        return ["cover", "chapter", "content"]
    if slide_type in {"references", "summary"}:
        return ["ending", "content", "cards"]
    if visual_type == "image":
        return ["text_visual", "visual", "content"]
    if visual_type == "chart":
        return ["data", "content", "cards"]
    if slide_type in {"objectives", "activity", "quiz", "diagram"}:
        return ["cards", "content", "text_visual"]
    return ["content", "cards", "text_visual"]


def choose_reference_slide(slide: dict, catalog: list[dict],
                           used: dict[int, int]) -> dict:
    """与 OpenTutor 相同的选择键：先版式族，再（使用次数, 与8槽的偏离）。"""
    for kind in _preferred_kinds(slide):
        candidates = [item for item in catalog
                      if (item.get("classification") or {}).get("layout_kind") == kind]
        if candidates:
            return min(candidates, key=lambda item: (
                used.get(int(item["index"]), 0),
                abs(len(item.get("slots") or []) - 8)))
    return min(catalog, key=lambda item: used.get(int(item["index"]), 0))


def plan_pages(deck: dict, catalog: list[dict]) -> tuple[list[dict], list[dict]]:
    """返回 (instances, mapping_report)。LLM 只做槽位文字映射；选择键是确定性的。"""
    used: dict[int, int] = {}
    selected: list[tuple[dict, dict]] = []
    for slide in deck.get("slides") or []:
        reference = choose_reference_slide(slide, catalog, used)
        index = int(reference["index"])
        used[index] = used.get(index, 0) + 1
        selected.append((slide, reference))

    mapping_input = [
        {
            "page_id": str(slide.get("id") or f"slide-{position}"),
            "semantic_slide": {key: slide.get(key) for key in (
                "type", "title", "subtitle", "bullets", "content",
                "speaker_notes")},
            "source_slide": reference["index"],
            "slots": [
                {
                    "slot_id": slot.get("slot_id"),
                    "role": slot.get("role"),
                    "original_text": slot.get("text", ""),
                    "geometry": slot.get("geometry", {}),
                    "font_size_px": ((slot.get("text_metrics") or {})
                                     .get("font_size_px")),
                }
                for slot in reference.get("slots") or []
                if slot.get("slot_id") and slot.get("text")
            ],
        }
        for position, (slide, reference) in enumerate(selected, 1)
    ]
    prompt = f"""将语义课件内容填入已经选定的 PowerPoint 参考页文本槽。
只替换承载课程内容的文本槽；Logo、公司名、页码、网址、版权可以不列入 replacements。
参考页自带的示例占位文字（Lorem ipsum 等英文占位段落、"汇报人：××""汇报部门：××"等示例标签）
不得原样保留：与课程可对应的改写（如汇报人→主讲教师、汇报部门→课程名），
纯占位段落用语义页的副标题或说明填充；无对应内容时用课程标题或日期等中性信息。
标题放入合适的标题槽，正文和要点按空间（geometry 与 font_size_px 估算容量）拆分；
槽的现有文字长度指示其容量，新文字不应显著超过原槽长度。
不得编造 page_id、source_slide 或 slot_id。
输出严格 JSON：{{"pages":[{{"page_id":"","source_slide":1,"replacements":[{{"slot_id":"","text":""}}]}}]}}。
输入：{json.dumps(mapping_input, ensure_ascii=False)}"""
    parsed = llm.json_call(
        "你是 PowerPoint 原生模板内容映射专家，只输出严格 JSON。", prompt)
    pages = parsed.get("pages") if isinstance(parsed, dict) else None
    if not isinstance(pages, list):
        raise llm.LLMError("模型未返回页面映射。")
    by_page_id = {str(p.get("page_id")): p for p in pages if isinstance(p, dict)}

    instances = []
    report = []
    for position, (slide, reference) in enumerate(selected, 1):
        page_id = str(slide.get("id") or f"slide-{position}")
        mapped = by_page_id.get(page_id)
        if not mapped or int(mapped.get("source_slide") or 0) != int(
                reference["index"]):
            # 模型伪造/漏页：丢弃映射，退化为原槽文字不动（保设计不空白）
            replacements = _fallback_replacements(slide, reference)
            note = "模型映射缺失，已用规则回退填充"
        else:
            valid_slots = {str(s.get("slot_id"))
                           for s in reference.get("slots") or []}
            replacements = [
                {"slot_id": str(item["slot_id"]),
                 "text": str(item.get("text") or "")}
                for item in mapped.get("replacements") or []
                if isinstance(item, dict)
                and str(item.get("slot_id")) in valid_slots
                and str(item.get("text") or "").strip()
            ]
            note = ""
        instances.append({
            "page_id": page_id,
            "source_slide": int(reference["index"]),
            "purpose": str(slide.get("type") or "content"),
            "replacements": replacements,
        })
        report.append({
            "page_id": page_id,
            "semantic_title": slide.get("title", ""),
            "source_slide": int(reference["index"]),
            "layout": (reference.get("classification") or {}).get(
                "layout_label", ""),
            "slot_count": len(replacements),
            "note": note,
        })
    return instances, report


def _fallback_replacements(slide: dict, reference: dict) -> list[dict]:
    """无 LLM 映射时的规则回退：标题槽放标题，正文槽按顺序放要点。"""
    slots = [s for s in reference.get("slots") or [] if s.get("slot_id")]
    title_slots = [s for s in slots
                   if "title" in str(s.get("role") or "")] or slots[:1]
    body_slots = [s for s in slots if s not in title_slots]
    replacements: list[dict] = []
    if title_slots:
        replacements.append({"slot_id": str(title_slots[0]["slot_id"]),
                             "text": str(slide.get("title") or "")[:80]})
    lines = list(slide.get("bullets") or [])
    if slide.get("content"):
        lines = [slide["content"]] + lines
    for slot, line in zip(body_slots, lines):
        replacements.append({"slot_id": str(slot["slot_id"]),
                             "text": str(line)[:int(
                                 max(20, len(str(slot.get("text") or "")) * 1.3))]})
    return replacements


def revise_page(slide: dict, reference: dict, instruction: str,
                source_slide: int | None = None) -> dict:
    """单页修订：instruction -> 完整替换集（+可选换参考页）。沿用 lab 契约。"""
    target = reference if source_slide is None else {
        **reference, "index": source_slide}
    slots = [
        {
            "slot_id": slot.get("slot_id"),
            "role": slot.get("role"),
            "original_text": slot.get("text", ""),
            "geometry": slot.get("geometry", {}),
        }
        for slot in reference.get("slots") or []
        if slot.get("slot_id") and slot.get("text")
    ]
    if source_slide is not None:
        slots = [
            {
                "slot_id": slot.get("slot_id"),
                "role": slot.get("role"),
                "original_text": slot.get("text", ""),
                "geometry": slot.get("geometry", {}),
            }
            for slot in target.get("slots") or []
            if slot.get("slot_id") and slot.get("text")
        ]
    prompt = f"""把一页语义课件填入指定 PowerPoint 参考页。
只替换课程内容槽，保留 Logo、页码、网址和版权。
参考页自带的示例占位文字（Lorem ipsum、示例汇报人等）不得原样保留，按教师意见或语义页内容改写。
不得编造 slot_id。只输出严格 JSON：{{"replacements":[{{"slot_id":"","text":""}}]}}。
教师修改意见：{instruction}
语义页：{json.dumps(slide, ensure_ascii=False)}
参考页编号：{target['index']}
文本槽：{json.dumps(slots, ensure_ascii=False)}"""
    parsed = llm.json_call(
        "你是 PowerPoint 原生模板单页映射专家，只输出严格 JSON。", prompt)
    valid_slots = {str(item["slot_id"]) for item in slots}
    replacements = [
        {"slot_id": str(item["slot_id"]), "text": str(item.get("text") or "")}
        for item in parsed.get("replacements") or []
        if isinstance(item, dict) and str(item.get("slot_id")) in valid_slots
    ]
    payload = {"replacements": replacements}
    if source_slide is not None:
        payload["source_slide"] = int(source_slide)
    return payload
