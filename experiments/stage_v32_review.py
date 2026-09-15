# -*- coding: utf-8 -*-
"""Append the v3.2 card (costume fix + rebuilt photo moment) to the review page."""
import io, sys
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
p = Path(r'output\creative_v2\concert30_v2_review.html')
s = p.read_text(encoding='utf-8')
if 'v32_master' in s:
    print('present'); raise SystemExit(0)
block = """
<section style="margin-top:36px;border:2px solid #22d3ee;border-radius:12px;padding:20px;background:#083344;color:#ecfeff">
<h2>v3.2 — 定稿 (30.0s / 1080p30)：红裙修复 + 搂肩合影重建</h2>
<p>针对你的两点反馈：①<b>酒红上衣问题根因</b>=参考包里红裙全身照的服装渗色——参考包 v5 把红裙换成<b>人脸裁切</b>（几何锚保留、服装不可见）+新增服装硬约束"黑色素面上衣、禁止复制参考照片服装"，S2 重新生成（黑衣✓）后再生成一版择优，并跳过开场弱帧；②<b>搂肩合影整段重做</b>：9 参考包（几何硬化+服装约束）重新生成，逐脸角色映射后链式修复——实测发现修复运行时的人脸序号与检测脚本相反，修正刀序后：<b>她 0.75–0.79（全片最高段恰在合影瞬间），视觉判级"真实照片"</b>（皮肤纹理/镜片物理反光/搂肩无穿模），他"高度吻合华晨宇本人"。</p>
<video controls width="960" src="concert30_hcy_flowers_v32_master.mp4"></video>
<p><b>身份门禁（母版密采样）</b>：女生 S2 <b>0.722</b> / S3 0.770 / S4-S5 0.767 / S6合影 0.750 / S6退场 0.776；华晨宇 真实段 0.71/0.78、生成修复段 0.60。五窗全 ≥0.72。</p>
</section>
"""
s = s.replace('</body>', block + '\n</body>')
p.write_text(s, encoding='utf-8')
print('v3.2 staged')
