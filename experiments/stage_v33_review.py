# -*- coding: utf-8 -*-
"""Append the v3.3 card (position-split pair repair) to the review page."""
import io, sys
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
p = Path(r'output\creative_v2\concert30_v2_review.html')
s = p.read_text(encoding='utf-8')
if 'v33_master' in s:
    print('present'); raise SystemExit(0)
block = """
<section style="margin-top:36px;border:2px solid #a3e635;border-radius:12px;padding:20px;background:#1a2e05;color:#f7fee7">
<h2>v3.3 — 合影窗交叉换脸根治 (30.0s / 1080p30)</h2>
<p>你反馈的 25–27 秒问题根因：修复器的人脸序号<b>逐帧漂移</b>，且歌手的舞台妆（红唇/细眉）被性别分类器误判为女性——按序号或按性别的定向修复都会把"她的脸"错打到他脸上。根治法=<b>位置分割修复</b>：两人位置全程不交叉（他恒左/她恒右，实测边界 x=633/634），把画面沿边界切成左右两半，各自单独修复（单脸输入=序号无歧义），再拼接回。逐帧角色核验：<b>每一帧</b>他 0.58–0.66（像华晨宇本人、无女性化）/她 0.75–0.82；拼接缝在闪光灯画面中不可见。</p>
<video controls width="960" src="concert30_hcy_flowers_v33_master.mp4"></video>
<p><b>门禁</b>：女生 S2 0.722 / S3 0.770 / S4-S5 0.766 / S6退场 0.784；华晨宇 真实段 0.71/0.78、生成段 0.60、合影窗 0.618（修复后新高）。</p>
</section>
"""
s = s.replace('</body>', block + '\n</body>')
p.write_text(s, encoding='utf-8')
print('v3.3 staged')
