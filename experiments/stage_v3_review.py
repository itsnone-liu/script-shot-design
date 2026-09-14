# -*- coding: utf-8 -*-
"""Stage the v3 complete-story master into the review page."""
import io, sys
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
p = Path(r'output\creative_v2\concert30_v2_review.html')
s = p.read_text(encoding='utf-8')
if 'v3_master' in s:
    print('present'); raise SystemExit(0)
block = """
<section style="margin-top:36px;border:2px solid #4ade80;border-radius:12px;padding:20px;background:#14532d;color:#f0fdf4">
<h2>v3 成片《被卷进高潮》— 完整剧情版 (30.0s / 1080p30 / 真实母轨)</h2>
<p>按你的审看意见重做：①华晨宇改用同款参考图路线生成（人脸裁切锚+SameFace 0.5+硬属性），生成后用 ReActor 把脸逐帧换回真实照片几何——光影全程生成域统一，剧情完整；②女生段重造演唱会真实感：追光周围黑暗+荧光棒海洋+人头攒动，挤过人群而非走通道；③新增剧情点：他俯身握住她的手拉上舞台 → 舞台举花束同跳跃 → 闪光灯合影 → 她挥手退场。</p>
<video controls width="960" src="concert30_hcy_flowers_v3_master.mp4"></video>
<p><b>身份门禁（母版窗口密采样）</b>：女生 S2追光 0.58 / S3穿人群 0.75 / S4-S5拉上台+举花 0.75 / S6合影 0.78（峰 0.811）；华晨宇 真实开闭幕 0.71/0.77、生成修复双人段 0.60-0.69。全部窗口过线，无串脸。</p>
</section>
"""
s = s.replace('</body>', block + '\n</body>')
p.write_text(s, encoding='utf-8')
print('v3 staged')
