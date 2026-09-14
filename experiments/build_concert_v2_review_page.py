# -*- coding: utf-8 -*-
"""Build a no-generation v2 review/selection page."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "creative_v2"
OUT.mkdir(parents=True, exist_ok=True)

html = r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>concert30 v2 重新设计</title><style>
body{margin:0;background:#08080b;color:#f5f5f7;font-family:"Microsoft YaHei",system-ui,sans-serif;line-height:1.65}main{max-width:1080px;margin:auto;padding:30px 20px 80px}
h1{font-size:34px}.red{color:#ff445e}.badge{display:inline-block;padding:3px 10px;border:1px solid #ff445e;border-radius:99px;color:#ff778a;font-size:13px}.card{background:#15151b;border:1px solid #30303a;border-radius:12px;padding:16px 18px;margin:12px 0}.pick{border-left:5px solid #ff445e}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}.time{color:#ff778a;font-weight:700}.muted{color:#aaa}.gate{background:#211117;border:1px solid #7d293a;padding:14px;border-radius:10px}a{color:#8cc5ff}li{margin:6px 0}
</style></head><body><main>
<p class="red">CONCERT30 · V2 RESET</p><h1>《被卷进高潮》<span class="badge">DRAFT · 未批准 · 付费锁定</span></h1>
<div class="gate"><b>v1 已否决并锁死。</b>新版本不使用生成出来的“相似女生”，不以银灰发/红麦克风替代华晨宇身份，也不再拍慢慢走上台。</div>
<h2>一句话</h2><p>一场正在高速运转的华晨宇演唱会，在歌曲高潮中突然把台下抱花女生卷进现场爆点；献花和合影只是高潮里的两个重拍，演唱从未停止。</p>
<h2>30秒音频先行时间轴</h2>
<div class="card"><span class="time">0.0–4.5s</span> 华晨宇已在唱高潮：汗湿面部极近景 → 鼓槌砸下 → 体育场超广角 → 他冲向延伸台；平均镜长0.8–1.2秒。</div>
<div class="card"><span class="time">4.5–8.5s</span> 主唱强拍/长音上扬，他指向看台；追光高速横扫红海，在强拍上击中抱花女生；周围尖叫、手机齐举。</div>
<div class="card"><span class="time">8.5–13.0s</span> 上台过程压成鼓点蒙太奇：抱紧花 → 安保开通道 → 快步冲过 → 鞋踩台阶 → 华晨宇边唱边伸手 → 她进入追光。禁止慢走。</div>
<div class="card"><span class="time">13.0–18.0s</span> 他一手持麦继续唱，一手在间奏重拍接花；立即举花并带她向舞台中央移动，不做停顿式仪式。</div>
<div class="card"><span class="time">18.0–24.0s</span> 华晨宇把花举给十万人看，LED灯阵由中心炸向全场；女生在身侧跟节拍跳，大屏切两人同框。</div>
<div class="card"><span class="time">24.0–30.0s</span> 连拍合影三次白闪：双人近景 → LED大屏 → 体育场大全景；最后重拍回华晨宇举花继续唱，女生挥手退出，能量不停。</div>
<h2>歌曲与同场造型三选一</h2><div class="grid">
<div class="card pick"><h3>A · 推荐</h3><b>2024南昌站《疯人院》电音版+尾奏</b><p>电子脉冲和尾奏强拍最适合快切、追光、接花、举花、白闪合影。</p><a href="https://www.bilibili.com/video/BV1dZvdePEyp/">公开现场参考</a></div>
<div class="card"><h3>B</h3><b>2024烟台站《齐天大圣》改编版</b><p>戏剧性与舞台动作强，适合冲向延伸台；需选密集窗口。</p><a href="https://www.bilibili.com/video/BV1RH4y1u7gs/">公开现场参考</a></div>
<div class="card"><h3>C</h3><b>2024体育馆开场版《向阳而生》</b><p>万人规模与观众参与最好，攻击性略弱于电音版。</p><a href="https://www.bilibili.com/video/BV1a1tCeuEt6/">公开现场参考</a></div></div>
<h2>双真人技术链</h2><ol><li>女生：直接输入5张原始照片；不经过“重画参考图”。</li><li>华晨宇：从所选同一场次建立H1–H5公开参考包，不跨年、不混发型。</li><li>主生成：MiniMax H3 Ref2VA <code>2093518439926218753</code>，约6个4–6秒高能容器，支持多图与参考音频。</li><li>后处理：分别跟踪两张脸，角色隔离后顺序修复，防串脸。</li><li>门禁：两人清晰正脸median≥0.60，英雄/合影帧≥0.70，单帧底线0.50，交叉身份差≥0.12。</li></ol>
<h2>声音政策</h2><p>使用用户指定/提供的真实现场30秒作为母轨；不生成或模仿华晨宇歌声。生成阶段可将分段音频作为节奏参考，后期必须重新铺回真实母轨。</p>
<div class="gate"><b>下一步：</b>回复“选A / 选B / 选C”，或直接发你要用的现场视频/30秒音频。选定后才建立华晨宇参考包和精确节拍合同。</div>
</main></body></html>'''
(OUT / "concert30_v2_review.html").write_text(html, encoding="utf-8")
print(OUT / "concert30_v2_review.html")
