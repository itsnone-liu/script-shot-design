"""stylecard.py —— 模板风格识别：布局(lab) + 色彩/字体(OOXML) + 风格描述(LLM)。

三源合一：
1. lab classification 汇总 -> 布局清单（封面/章节/卡片/图文…各多少页）
2. pptx theme1.xml + python-pptx run 统计 -> 色板（hex 频次）+ 字体体系（名称/字号分布）
3. LLM 综合上述机器信号 -> 一段面向用户的风洛卡（不引入模板文件之外的事实）
"""
from __future__ import annotations

import io
import re
import zipfile
from collections import Counter
from pathlib import Path

from pptx import Presentation

THEME_COLOR_KEYS = ["dk1", "lt1", "dk2", "lt2", "accent1", "accent2",
                    "accent3", "accent4", "accent5", "accent6", "hlink"]


def _hex_to_rgb(value: str):
    value = value.lstrip("#")
    if len(value) == 6:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    return None


def _rgb_to_hex(rgb: tuple) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _theme_from_zip(path: Path) -> dict:
    """读 ppt/theme/theme1.xml：字体方案 + 颜色方案。"""
    out = {"theme_colors": [], "major_font": "", "minor_font": ""}
    try:
        with zipfile.ZipFile(path) as archive:
            names = [n for n in archive.namelist()
                     if re.fullmatch(r"ppt/theme/theme\d+\.xml", n)]
            if not names:
                return out
            xml = archive.read(sorted(names)[0]).decode("utf-8", "ignore")
    except (zipfile.BadZipFile, OSError):
        return out

    major = re.search(
        r"<a:majorFont>.*?<a:latin typeface=\"([^\"]*)\"", xml, re.S)
    minor = re.search(
        r"<a:minorFont>.*?<a:latin typeface=\"([^\"]*)\"", xml, re.S)
    major_ea = re.search(
        r"<a:majorFont>.*?<a:ea typeface=\"([^\"]*)\"", xml, re.S)
    minor_ea = re.search(
        r"<a:minorFont>.*?<a:ea typeface=\"([^\"]*)\"", xml, re.S)
    out["major_font"] = (major.group(1) if major else "") or \
        (major_ea.group(1) if major_ea else "") or ""
    out["minor_font"] = (minor.group(1) if minor else "") or \
        (minor_ea.group(1) if minor_ea else "") or ""

    scheme = re.search(r"<a:clrScheme.*?</a:clrScheme>", xml, re.S)
    if scheme:
        block = scheme.group(0)
        for key in THEME_COLOR_KEYS:
            match = re.search(
                rf'<a:{key}>.*?(?:srgbClr val="([0-9A-Fa-f]{{6}})"'
                rf'|sysClr[^/]*lastClr="([0-9A-Fa-f]{{6}})")', block, re.S)
            if match:
                value = match.group(1) or match.group(2)
                out["theme_colors"].append(
                    {"role": key, "hex": f"#{value.upper()}"})
    return out


def _run_stats(path: Path, sample_limit: int = 60) -> dict:
    """run 级字体名/字号/颜色频次（抽前 N 页避免大模板卡顿）。"""
    fonts: Counter = Counter()
    sizes: Counter = Counter()
    colors: Counter = Counter()
    ea_fonts: Counter = Counter()
    try:
        prs = Presentation(str(path))
    except Exception:
        return {"fonts": [], "sizes": [], "colors": []}
    for slide in list(prs.slides)[:sample_limit]:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    text = (run.text or "").strip()
                    if not text:
                        continue
                    font = run.font
                    if font.name:
                        fonts[font.name] += len(text)
                    try:
                        if font.size is not None:
                            sizes[round(font.size.pt, 1)] += len(text)
                    except Exception:
                        pass
                    try:
                        rgb = font.color and font.color.rgb
                        if rgb is not None:
                            colors[f"{rgb}"] += len(text)
                    except Exception:
                        pass
                    # 东亚字体（中文场景主要字体）
                    try:
                        rPr = run._r.find(
                            "{http://schemas.openxmlformats.org/drawingml/2006/main}rPr")
                        if rPr is not None:
                            ea = rPr.find(
                                "{http://schemas.openxmlformats.org/drawingml/2006/main}ea")
                            if ea is not None and ea.get("typeface"):
                                ea_fonts[ea.get("typeface")] += len(text)
                    except Exception:
                        pass
    merged = Counter()
    for name, weight in fonts.items():
        merged[name] += weight
    for name, weight in ea_fonts.items():
        merged[name] += weight
    return {
        "fonts": [{"name": n, "weight": w} for n, w in merged.most_common(6)],
        "ea_fonts": [{"name": n, "weight": w}
                     for n, w in ea_fonts.most_common(4)],
        "sizes": [{"pt": s, "weight": w} for s, w in sizes.most_common(8)],
        "colors": [{"hex": f"#{c}", "weight": w}
                   for c, w in colors.most_common(8)],
        "slide_size": (prs.slide_width and prs.slide_height) and {
            "emu": [prs.slide_width, prs.slide_height],
            "ratio": round(prs.slide_width / prs.slide_height, 3)},
    }


def layout_summary(catalog: list[dict]) -> dict:
    kinds: Counter = Counter()
    density: Counter = Counter()
    for item in catalog:
        cls = item.get("classification") or {}
        kinds[cls.get("layout_label") or cls.get("layout_kind") or "?"] += 1
        density[cls.get("density") or "?"] += 1
    return {
        "slide_count": len(catalog),
        "layout_kinds": [{"kind": k, "pages": v} for k, v in kinds.most_common()],
        "density": dict(density),
    }


def build_style_card(pptx_path: Path, catalog: list[dict]) -> dict:
    theme = _theme_from_zip(pptx_path)
    runs = _run_stats(pptx_path)
    layout = layout_summary(catalog)
    card = {"theme": theme, "runs": runs, "layout": layout,
            "summary": "", "palette": [c["hex"] for c in theme["theme_colors"]][:8]}
    card["summary"] = _summarize(card)
    return card


def _summarize(card: dict) -> str:
    from . import llm
    signals = {
        "色板": card["theme"]["theme_colors"],
        "主题字体": {"标题": card["theme"]["major_font"],
                    "正文": card["theme"]["minor_font"]},
        "实际使用字体": card["runs"]["fonts"],
        "字号分布(pt)": [s["pt"] for s in card["runs"]["sizes"]][:6],
        "高频文字颜色": card["runs"]["colors"][:5],
        "版式构成": card["layout"]["layout_kinds"],
        "画幅比例": (card["runs"].get("slide_size") or {}).get("ratio"),
    }
    prompt = f"""你是演示设计分析师。以下是从一个 PowerPoint 模板文件机器提取的信号（无任何推测数据）：
{signals}
用中文写模板风格卡，4-6 行要点，覆盖：色彩体系（主色/辅色及其感受）、字体体系（中西文、标题/正文层级）、
版式风格（版式构成反映的设计语言）、适合的课件场景与文字密度建议。
只依据给定信号描述，不得虚构具体数值之外的事实。直接输出要点正文。"""
    try:
        return llm.chat("你是严谨的演示设计分析师。", prompt, temperature=0.2)
    except llm.LLMError as exc:
        return f"（风格描述生成失败：{exc}；机器信号见 JSON 字段）"
