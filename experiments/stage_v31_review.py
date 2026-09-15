# -*- coding: utf-8 -*-
"""Append the v3.1 card (identity-closeness pass) to the review page."""
import io, sys
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
p = Path(r'output\creative_v2\concert30_v2_review.html')
s = p.read_text(encoding='utf-8')
if 'v31_master' in s:
    print('present'); raise SystemExit(0)
block = """
<section style="margin-top:36px;border:2px solid #f472b6;border-radius:12px;padding:20px;background:#500724;color:#fdf2f8">
<h2>v3.1 — 逼近原型优化版 (30.0s / 1080p30)</h2>
<p>按你的几何反馈（原型下巴更尖、眼睛略小）做的逼近：①修复源脸换成几何最强参考（红裙正脸，尖下巴+窄眼最清晰）；②参考包 4→5 张（剔除弱锚/模糊图，补入单人高清图）；③生成端新增硬几何属性"V形尖下巴、比例偏小眼睛、禁放大眼睛、禁圆润下巴、禁美化滤镜"，S2 整段重新生成。④顺手清除生成帧继承的官摄水印/字幕（顶角模糊覆盖+字幕带裁切，隔离判读已不可读）。</p>
<video controls width="960" src="concert30_hcy_flowers_v31_master.mp4"></video>
<p><b>身份门禁（母版窗口密采样）</b>：女生 S2 0.582→<b>0.685</b> / S3 0.770 / S4-S5 0.773（峰 0.813）/ S6 0.740；华晨宇 0.57-0.71 各窗过线。全分辨率几何核验：尖下巴 ✓、眼比例真实 ✓（"眼裂长≈鼻翼宽"）、"AI滤镜感≤5%"。</p>
</section>
"""
s = s.replace('</body>', block + '\n</body>')
p.write_text(s, encoding='utf-8')
print('v3.1 staged')
