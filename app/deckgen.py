"""deckgen.py —— 教案 → 课件文字（语义页 deck JSON），及课件文字容错解析。

解析链移植自 OpenTutor teacher.py 的 _parse_deck_json / _deck_from_markdown：
  剥 ``` 围栏 -> json.loads -> 正则捞首个 JSON 对象 -> wrapper(deck/presentation/
  slide_deck) 展开 -> slides/pages 兼容 -> Markdown 分页回退。
"""
from __future__ import annotations

import json
import re

from . import llm

DECK_SCHEMA_HINT = """{
  "title": "课件标题",
  "slides": [
    {"id": "slide-1", "type": "title|content|objectives|activity|quiz|diagram|summary|references",
     "title": "页标题", "subtitle": "副标题（仅封面需要，可空）",
     "bullets": ["要点1", "要点2"],
     "content": "整段正文（与 bullets 二选一，可空）",
     "speaker_notes": "讲稿提示",
     "visual": {"type": "none|chart|diagram", "description": "视觉建议"}}
  ]
}"""

GENERATE_SYSTEM = "你是课件内容设计专家，只输出严格 JSON。"


def deck_from_lesson_plan(lesson_markdown: str, *, slide_target: int = 0,
                          extra_instructions: str = "") -> dict:
    """教案 Markdown -> 语义页 deck JSON（LLM）。"""
    target = f"目标 {slide_target} 页左右。" if slide_target else "页数按内容自然划分。"
    prompt = f"""把下面的教案转成课件文字内容（每页标题+要点，供后续套用 PowerPoint 模板版式）。
要求：
- 首页为封面（type=title，含课题与副标题），其后按教学节奏分页：目标、讲解、例题、活动、小结等；
- 每页 3-5 个要点，单要点不超过 40 字，控制信息密度；讲解性长文放入 speaker_notes 而不是页面；
- 严格依据教案，不虚构教案外的核心知识；{target}
- 只输出严格 JSON，结构：
{DECK_SCHEMA_HINT}

教师补充要求：{extra_instructions.strip() or "无"}

教案：
{lesson_markdown[:60000]}"""
    deck = llm.json_call(GENERATE_SYSTEM, prompt)
    return normalize_deck(deck)


def parse_courseware_text(text: str) -> dict:
    """课件文字内容（JSON 或 Markdown/纯文本）-> 语义页 deck JSON。"""
    stripped = text.strip()
    if not stripped:
        raise ValueError("课件文字内容为空。")
    if stripped[0] in "[{":
        try:
            return normalize_deck(json.loads(
                re.sub(r"^```(?:json)?\s*|\s*```$", "", stripped)))
        except json.JSONDecodeError:
            pass
    deck = _deck_from_markdown(stripped)
    return normalize_deck(deck)


def normalize_deck(deck: dict) -> dict:
    """统一 deck 顶层/页字段，丢坏页。"""
    if not isinstance(deck, dict):
        raise ValueError("课件结构不是对象。")
    for wrapper in ("deck", "presentation", "slide_deck"):
        wrapped = deck.get(wrapper)
        if isinstance(wrapped, dict):
            deck = wrapped
            break
    if not isinstance(deck.get("slides"), list) and isinstance(
            deck.get("pages"), list):
        deck["slides"] = deck.pop("pages")
    slides = [s for s in deck.get("slides") or [] if isinstance(s, dict)]
    if not slides:
        raise ValueError("课件没有有效页面。")
    clean = []
    for position, slide in enumerate(slides[:50], 1):
        page_id = str(slide.get("id") or f"slide-{position}")
        clean.append({
            "id": page_id,
            "type": str(slide.get("type") or
                        ("title" if position == 1 else "content")),
            "title": str(slide.get("title") or f"第 {position} 页")[:120],
            "subtitle": str(slide.get("subtitle") or "")[:200],
            "bullets": [str(b)[:240] for b in (slide.get("bullets") or [])[:8]],
            "content": str(slide.get("content") or "")[:2000],
            "speaker_notes": str(slide.get("speaker_notes") or "")[:2000],
            "visual": (slide.get("visual")
                       if isinstance(slide.get("visual"), dict)
                       else {"type": "none", "description": ""}),
        })
    deck["slides"] = clean
    deck.setdefault("title", clean[0]["title"])
    return deck


def _deck_from_markdown(markdown: str) -> dict:
    """Markdown/纯文本 -> deck（移植自 OpenTutor，模型不守 JSON 契约时的回退）。"""
    sections = [s.strip() for s in re.split(r"(?m)^#{1,3}\s+", markdown) if s.strip()]
    if len(sections) < 2:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", markdown) if p.strip()]
        sections = paragraphs[:40]
    slides = []
    for index, section in enumerate(sections[:50], 1):
        lines = [ln.strip() for ln in section.splitlines() if ln.strip()]
        if not lines:
            continue
        title = re.sub(r"^[\-*\d.、\s]+", "", lines[0])[:100] or f"第 {index} 页"
        bullets = []
        for line in lines[1:]:
            value = re.sub(r"^[\-*+\d.、）)\s]+", "", line).strip()
            if value:
                bullets.append(value[:240])
        slides.append({
            "id": f"slide-{index}",
            "type": "title" if index == 1 else "content",
            "title": title,
            "subtitle": "" if index > 1 else (bullets[0] if bullets else ""),
            "bullets": [] if index == 1 else bullets[:7],
            "content": "",
            "speaker_notes": "",
            "visual": {"type": "none", "description": ""},
        })
    if not slides:
        raise ValueError("课件文字内容无法解析为页面。")
    return {
        "title": slides[0]["title"], "subtitle": slides[0].get("subtitle", ""),
        "warnings": ["输入非标准课件 JSON，已按 Markdown 自动分页；建议检查逐页内容。"],
        "slides": slides,
    }
