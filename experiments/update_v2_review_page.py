# -*- coding: utf-8 -*-
"""Embed the v2 master video into the v2 review page if not already present."""
import io, sys
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
p = Path(r'output\creative_v2\concert30_v2_review.html')
s = p.read_text(encoding='utf-8')
if 'v2_master' in s:
    print('already present'); raise SystemExit(0)
block = """
<section style="margin-top:36px;border:2px solid #ffd166;border-radius:12px;padding:20px;background:#1c1917;color:#f5f5f4">
<h2>v2 成片《被卷进高潮》— 混合管线首版 (30.0s / 1080p30 / 真实母轨 313-343s)</h2>
<p>管线：真实南昌现场做华晨宇主干 + 女生原始照片直接喂入生成底片（Ref2VA 4图参考 + SameFace 0.5）+ ReActor 逐帧身份修复（S2）+ 节拍剪辑（1.6x 冲刺/真实插入/频闪收尾）。</p>
<video controls width="960" src="concert30_hcy_flowers_v2_master.mp4"></video>
<p><b>身份门禁摘要</b>：华晨宇全部真实镜头（0.67-0.75 五处强锚）；女生 S2 追光段 median 0.707（14帧全≥0.64）、S6 median 0.639、S3 峰 0.734、S4 峰 0.693；跨角色无串脸（各自窗口边距≥0.25）。</p>
</section>
"""
s = s.replace('</body>', block + '\n</body>')
p.write_text(s, encoding='utf-8')
print('review page updated')
