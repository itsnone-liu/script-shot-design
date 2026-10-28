"""Blind review form builder for coffee30 v2《未发送》two-pass comparison.

Reads the take manifest AFTER generation, assigns shuffled blind codes
(seed recorded in the form so the shuffle is reproducible but not guessable
from file order), and emits one review form per pass plus the ablation pair.

  python experiments/build_unsent_blind_review.py [--seed 20261028]

Output: output/creative_v2/coffee30_v2_unsent/review/blind_review_form_v1.md
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "creative_v2" / "coffee30_v2_unsent"
MANIFEST = OUT / "asset_manifest.json"
FORM = OUT / "review" / "blind_review_form_v1.md"

AXES = [
    ("emotion_turn", "情绪转折可读性：能否指出情绪变化点及其契机"),
    ("reveal_clarity", "注意力揭示清晰度：她何时、因为什么发现杯与便签"),
    ("action_physics", "动作物理可信：取放/打字/捧杯是否可信、无凭空物件"),
    ("continuity", "镜间连续性：位置/手持物/服装/光向/蒸汽是否连贯"),
    ("rhythm", "节奏：骤停-悬停-阅读-兑现的长短对比是否可感"),
    ("overall", "整体完成度：作为32秒产品向短片的成立度"),
]
SCALE = "1-5 分（1=完全不成立，3=勉强成立，5=完全成立）"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20261028)
    args = parser.parse_args()

    if not MANIFEST.exists():
        print(f"manifest not found: {MANIFEST} (run after generation)")
        return 3
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    successes = [t for t in manifest.get("takes", []) if t.get("status") == "success" and t.get("outputs")]

    rng = random.Random(args.seed)
    candidates = [t["shot_id"] for t in successes]
    blind_codes = {shot_id: f"V{idx:02d}" for idx, shot_id in enumerate(rng.sample(candidates, len(candidates)), start=1)}

    lines = [
        "# 《未发送》两遍法盲评表 v1",
        "",
        f"- 盲码种子：{args.seed}（打乱可复现，评者不知哪个码是哪一遍）",
        f"- 成功take数：{len(successes)}；逐take评分，逐轴 " + SCALE,
        "- 拼接成片（每遍一部）在片尾贴盲码；对照实验take（N7/N8全指定 vs 裸动作）单独贴盲码",
        "",
        "## 评分轴",
        "",
    ]
    lines += [f"- **{code}** — {desc}" for code, desc in AXES]
    lines += ["", "## 逐take评分表", "", "| 盲码 | 文件 | " + " | ".join(code for code, _ in AXES) + " |", "|" + "---|" * (len(AXES) + 2)]
    for t in successes:
        file = Path(t["outputs"][0]).name
        lines.append(f"| {blind_codes[t['shot_id']]} | {file} | " + " | ".join(" " for _ in AXES) + " |")
    lines += [
        "",
        "## 成片对比（看完两部再填）",
        "",
        "- 哪一部情绪转折更清楚？为什么（一句话）：",
        "- 哪一部节奏更有长有短？例子：",
        "- 表情对照（N7/N8）：全指定 vs 裸动作，哪个表情更可读：",
        "",
        "## 映射（评完后再翻开）",
        "",
        "```json",
        json.dumps(blind_codes, ensure_ascii=False, indent=2),
        "```",
    ]

    FORM.parent.mkdir(parents=True, exist_ok=True)
    FORM.write_text("\n".join(lines), encoding="utf-8")
    print(f"review form: {FORM} ({len(successes)} takes, {len(AXES)} axes, seed {args.seed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
