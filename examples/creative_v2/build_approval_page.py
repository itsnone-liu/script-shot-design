"""Build a static, self-contained user approval page for coffee30 C1 v1."""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "examples" / "creative_v2"
OUT = ROOT / "output" / "creative_v2" / "coffee30_dont_wake_her_approval"


def load(name: str):
    return json.loads((BASE / name).read_text(encoding="utf-8"))


def e(value) -> str:
    return html.escape(str(value), quote=True)


def main() -> None:
    concept_doc = load("coffee30_concepts_v2.json")
    concept = next(c for c in concept_doc["candidates"] if c["id"] == "C1_dont_wake_her")
    seg_a = load("coffee30_dont_wake_her_segA_v1.json")
    seg_b = load("coffee30_dont_wake_her_segB_v1.json")
    plan = load("coffee30_dont_wake_her_production_plan_v1.json")
    shots = [("A", s) for s in seg_a["internal_shots"]] + [("B", s) for s in seg_b["internal_shots"]]

    strategy = concept["creative_strategy"]
    cards = []
    global_start = 0.0
    for segment, shot in shots:
        start = shot["start"] + (15 if segment == "B" else 0)
        end = shot["end"] + (15 if segment == "B" else 0)
        d = shot["cinematic_design"]
        cards.append(f"""
        <article class="shot">
          <header><b>{e(shot['shot_id'])}</b><span>{start:g}–{end:g}s · {e(shot['shot_size'])}</span></header>
          <div class="frame">{e(d['composition_logic'])}</div>
          <h3>{e(d['narrative_job'])}</h3>
          <p><strong>动作：</strong>{e(shot['subject_action'])}</p>
          <p><strong>微表演：</strong>{e(d['performance_detail']['micro_action'])}</p>
          <p><strong>顺序：</strong>{e(d['performance_detail']['reaction_order'])}</p>
          <p class="question"><strong>观众问题：</strong>{e(d['audience_knowledge']['question'])}</p>
          <footer>并发事件≤{e(d['event_budget']['max_concurrent_events'])} · {e(shot['transition_in'])}</footer>
        </article>""")

    risk_rows = []
    for item in plan["shot_risk_budget"]:
        risk_rows.append(f"<tr><td>{e(item['shot'])}</td><td class='{e(item['risk'])}'>{e(item['risk'])}</td><td>{e(item['takes'])}</td><td>{e('；'.join(item['failure_modes']))}</td></tr>")

    approved = all(x["user_script_review"].get("status") == "approved" for x in (seg_a, seg_b))
    status_label = "已批准 C1 v1 · 关键帧与视频制作中" if approved else "待用户审批 · 尚未创建付费任务"
    action_title = "当前制作状态" if approved else "审批动作"
    action_body = (
        "<p><b>用户反馈：</b>先做C1，注意镜头设计。</p>"
        "<p>当前顺序：四张关键帧视觉验收 → A段3 take / B段4 take → 逐镜抽帧QA → 选片拼接。</p>"
        "<p>镜头审片硬标准：信息任务明确、三次险情构图不重复、微动作错峰、光向连续、最后回到咖啡。</p>"
        if approved else
        "<p>批准请回复：<code>批准 C1 v1</code></p>"
        "<p>修改请回复：<code>保留 C1，但修改……</code></p>"
        "<p>批准后才会：写入两份合同的 approved 字段 → 生成四张关键帧 → 运行 A3/B4 best-of-N → 抽帧 QA → 选片拼接。</p>"
    )

    page = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>《别吵醒她》创意审批页</title>
<style>
:root{{--bg:#0e1116;--panel:#171c24;--ink:#eef1f5;--muted:#9da9b8;--gold:#e5b862;--blue:#8ab4f8;--red:#ff8585}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:"Microsoft YaHei",system-ui,sans-serif;line-height:1.65}}
main{{max-width:1180px;margin:auto;padding:36px 24px 80px}}h1{{font-size:clamp(34px,6vw,72px);line-height:1.05;margin:.25em 0;color:#fff}}h2{{margin-top:58px;font-size:28px;border-left:4px solid var(--gold);padding-left:14px}}.eyebrow,.tag{{color:var(--gold);letter-spacing:.12em;text-transform:uppercase}}.lead{{max-width:800px;font-size:21px;color:#d4dae3}}.status{{display:inline-block;padding:8px 14px;border:1px solid var(--gold);border-radius:99px;color:var(--gold)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}}.box,.shot{{background:var(--panel);border:1px solid #2b3441;border-radius:14px;padding:18px}}.box strong{{display:block;color:var(--gold);margin-bottom:6px}}.ladder{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}.step{{padding:18px;background:#1d2430;border-radius:12px;border-top:3px solid var(--gold)}}
.timeline{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}}.shot header{{display:flex;justify-content:space-between;color:var(--gold);gap:12px}}.shot header span,.shot footer{{color:var(--muted);font-size:13px}}.shot h3{{font-size:18px;margin:14px 0 8px}}.shot p{{font-size:14px;margin:6px 0}}.shot .frame{{height:115px;margin:12px 0;background:linear-gradient(135deg,#252f3e,#121820);border-radius:9px;padding:14px;color:#bfc9d7;display:flex;align-items:end}}.question{{color:var(--blue)}}
table{{width:100%;border-collapse:collapse;background:var(--panel)}}td,th{{padding:11px;border-bottom:1px solid #303947;text-align:left;font-size:14px}}.critical{{color:#ff6262}}.high{{color:#ffab70}}.medium{{color:#f3da79}}.approve{{margin-top:55px;padding:25px;border:2px solid var(--gold);border-radius:14px;background:#1d1b16}}code{{background:#0a0c10;padding:3px 7px;border-radius:5px}}.fine{{color:var(--muted);font-size:13px}}
@media(max-width:700px){{.timeline,.ladder{{grid-template-columns:1fr}}}}
</style></head><body><main>
<p class="eyebrow">Coffee 30s · Creative V2 · Script-first</p><span class="status">{status_label}</span>
<h1>《别吵醒她》</h1><p class="lead">{e(concept['hook'])}</p>
<section><h2>为什么它不再平铺直叙</h2><div class="grid">
<div class="box"><strong>观众默认预期</strong>{e(strategy['audience_assumption'])}</div>
<div class="box"><strong>第一处偏离</strong>{e(strategy['expectation_break'])}</div>
<div class="box"><strong>世界规则</strong>{e(strategy['world_rule'])}</div>
<div class="box"><strong>结尾重释</strong>{e(strategy['ending_reframe'])}</div>
<div class="box"><strong>产品真相</strong>{e(strategy['product_truth'])}</div>
<div class="box"><strong>拒绝俗套</strong>{e(strategy['cliche_rejected'])}</div>
</div></section>
<section><h2>三级升级</h2><div class="ladder">{''.join(f'<div class="step"><b>0{i+1}</b><br>{e(x)}</div>' for i,x in enumerate(strategy['escalation_ladder']))}</div></section>
<section><h2>30 秒逐镜审片</h2><p class="fine">镜头卡展示的不是泛化“运镜词”，而是每镜的信息任务、动作顺序、微表演和事件密度。</p><div class="timeline">{''.join(cards)}</div></section>
<section><h2>生成风险与预算</h2><table><thead><tr><th>镜头</th><th>风险</th><th>诊断用takes</th><th>主要失败模式</th></tr></thead><tbody>{''.join(risk_rows)}</tbody></table>
<p>实际按 15 秒容器采样：A 段 <b>3</b> 次，B 段 <b>4</b> 次，批准后计划最多 <b>7</b> 次付费调用。</p></section>
<section class="approve"><h2 style="margin-top:0">{action_title}</h2>
{action_body}
<p class="fine">任何脚本修改都会把两份合同重新设为 pending；RunningHub SUCCESS 不替代产物和画面验收。</p></section>
</main></body></html>"""
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(page, encoding="utf-8")
    summary = {
        "status": "built",
        "shots": len(shots),
        "duration": sum(float(s["end"]) - float(s["start"]) for _, s in shots),
        "approval": [seg_a["user_script_review"]["status"], seg_b["user_script_review"]["status"]],
        "planned_paid_calls_after_approval": plan["container_budget"]["estimated_paid_calls_after_approval"],
    }
    (OUT / "page_manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
