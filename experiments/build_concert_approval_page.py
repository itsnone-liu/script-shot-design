# -*- coding: utf-8 -*-
"""Build the approval page for concert30-hcy-flowers v1 (static HTML, no paid calls)."""
import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "examples" / "concert30_hcy_flowers"
OUT = ROOT / "output" / "concert30_hcy_flowers_v1" / "approval"
OUT.mkdir(parents=True, exist_ok=True)

plan = json.loads((SRC / "production_plan_v1.json").read_text(encoding="utf-8"))
segA = json.loads((SRC / "segA_v1.json").read_text(encoding="utf-8"))
segB = json.loads((SRC / "segB_v1.json").read_text(encoding="utf-8"))

REFS = [
    ("ref06（主参考：红T恤正面）", "ref06_concert_poster_red_tee.jpg"),
    ("ref03（辅助：体育场自拍）", "ref03_stadium_selfie.jpg"),
    ("ref05（辅助：正面特写）", "ref05_dessert_tshirt.jpg"),
    ("ref01（辅助：裙装全身）", "ref01_burgundy_dress_fork.jpg"),
]
import base64, hashlib


def b64(p: Path) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode()


def shot_rows(seg: dict) -> str:
    rows = []
    for s in seg["internal_shots"]:
        rows.append(
            f"<tr><td><b>{s['shot_id']}</b><br><small>{s['start']}-{s['end']}s · {s['shot_size']} · {s['transition_in']}</small></td>"
            f"<td>{s['visual_state']}<br><small><b>动作</b> {s['subject_action']}<br><b>镜头</b> {s['camera_action']}<br><b>光</b> {s['lighting_state']}<br><b>出点</b> {s['end_state']}</small></td></tr>"
        )
    return "\n".join(rows)


ref_html = "\n".join(
    f'<figure><img src="{b64(SRC / "refs" / f)}"><figcaption>{cap}</figcaption></figure>'
    for cap, f in REFS
)

html = f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<title>审批 · 火星红的三十秒 v1</title>
<style>
body{{font-family:system-ui,'Microsoft YaHei',sans-serif;max-width:1080px;margin:24px auto;padding:0 16px;color:#1a1a1a;line-height:1.55}}
h1{{font-size:22px;border-bottom:3px solid #c62828;padding-bottom:8px}} h2{{font-size:17px;margin-top:28px;color:#c62828}}
table{{border-collapse:collapse;width:100%;font-size:13px}} th,td{{border:1px solid #ddd;padding:7px 9px;vertical-align:top;text-align:left}}
th{{background:#fdecea}} tr:nth-child(even){{background:#fafafa}} small{{color:#555}}
.pending{{display:inline-block;background:#fff3e0;color:#e65100;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600}}
.lock{{background:#e8f5e9;color:#1b5e20;padding:1px 8px;border-radius:10px;font-size:12px}}
.refs{{display:flex;gap:12px;flex-wrap:wrap}} .refs figure{{margin:0;width:200px;text-align:center;font-size:12px}}
.refs img{{width:200px;height:266px;object-fit:cover;border-radius:6px;border:1px solid #ccc}}
.risk{{background:#fff8e1;border-left:4px solid #f9a825;padding:8px 12px;margin:6px 0;font-size:13px}}
.gate{{background:#e8f5e9;border-left:4px solid #2e7d32;padding:8px 12px;margin:6px 0;font-size:13px}}
code{{background:#f5f5f5;padding:1px 5px;border-radius:3px}}
</style></head><body>
<h1>审批单 · 《火星红的三十秒》concert30-hcy-flowers <span class="pending">PENDING 等待批准</span></h1>
<p><b>内容</b>：她在华晨宇演唱会台上献花并合影 · 30 秒（2×15s 容器） · <code>script_version: concert30-hcy-flowers-v1</code></p>

<h2>0 · 创意一页纸</h2>
<p><b>logline</b>：十万人的红海之夜，一束花替她说完了所有没说出口的话。</p>
<ul>
<li><b>预期违背</b>：不是粉丝紧张的请求——是舞台向她走来：他走下半级台阶、俯身双手接花，最后侧身把大屏让给她。</li>
<li><b>世界规则</b>：追光在哪，世界中心就在哪。A 段光属于远处的舞台；追光停在她身上那一刻，规则宣告"今晚轮到你了"。</li>
<li><b>红色母题</b>：花束的红 → 麦克风的红 → 大屏的红 → 红海，最后一个红是她自己（红 T 恤）站进光里。</li>
<li><b>结尾重构</b>：白闪把合影洗成一张照片——时间被保存，而不是被消费。</li>
<li><b>三级递进</b>：暗处攥紧（紧张）→ 追光行走（临近）→ 递出与接住（高潮）→ 白闪定格（回甘）。</li>
</ul>

<h2>1 · 她的身份（来自你发的 9 张参考图）</h2>
<div class="refs">{ref_html}</div>
<p><span class="lock">身份锁</span> 鹅蛋脸 · 白皙肤 · <b>圆金属细框眼镜</b>（全程佩戴）· 深棕中分长发过肩 · 红棕哑光唇 · 片中着装=鲜红宽松长袖 T 恤（与 ref06 一致，呼应红色母题）。</p>
<p><b>他的形象</b>：清瘦 · 银灰挑染短发 · 黑色舞台衬衫 · <b>红色麦克风</b>（ref06 海报风格锚定）。<span class="risk" style="display:inline">风险明示：艺人相似度取决于模型先验，验收标准=可识别的华晨宇式舞台形象，非逐帧复刻</span></p>

<h2>2 · A 段《红海那头》（0-15s：看台 → 追光 → 通道 → 台口）</h2>
<table><tr><th style="width:130px">镜头</th><th>内容</th></tr>{shot_rows(segA)}</table>
<p><b>首帧</b>：{segA['first_frame']}<br><b>尾帧</b>：{segA['last_frame']}</p>

<h2>3 · B 段《俯身接花》（0-15s：递花 → 接花 → 并肩+大屏同框 → 合影 → 照片定格）</h2>
<table><tr><th style="width:130px">镜头</th><th>内容</th></tr>{shot_rows(segB)}</table>
<p><b>首帧</b>：{segB['first_frame']}<br><b>尾帧</b>：{segB['last_frame']}</p>

<h2>4 · 工作流（能力检查已完成，无需新建）</h2>
<p><b>关键帧·主选</b>：Flux Kontext 角色一致性 <code>{plan['capability_check']['primary']['workflow_id']}</code>（单参考图+指令改写，写实）<br>
<b>关键帧·备选</b>：PuLID+InstantID 人脸栈 <code>1930656665035845633</code>（特写兜底）· 双参考图分镜出图 <code>2054763247810686977</code><br>
<b>i2v</b>：MiniMax <code>2092512701252022274</code>（咖啡 C1 已验证：首尾帧锚定 15s/1056×576/24fps）</p>

<h2>5 · 预算与风险</h2>
<p>付费预算：关键帧 4 张（含 4 张返工余量）+ 视频 A/B 各 ≤2 take。</p>
<div class="risk"><b>高</b> B2 双人接花手部交互 → 关键帧阶段先验手部；i2v 动作收窄为"双手环抱入怀"</div>
<div class="risk"><b>中</b> 人群清晰化崩脸 → 永远 bokeh；<b>中</b> B3 大屏切换 i2v 不稳 → 弱化为"屏幕亮起同框"</div>
<div class="gate"><b>硬门</b>：你批准（两份合同同版本 approved）前，零付费调用。任何脚本修改都会重置审批。</div>

<h2>6 · 批准方式</h2>
<p>在飞书回复：<code>批准 concert30 v1</code>（可附修改意见，如"批准，但 B4 改成……"）。批准后流程：关键帧 4 张（先免费验收身份/构图）→ 你过目 → i2v A/B → 拼接 QA → 成片交付。</p>
</body></html>"""

(OUT / "index.html").write_text(html, encoding="utf-8")
print(f"approval page -> {OUT / 'index.html'} ({len(html)} chars)")
