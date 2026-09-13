# -*- coding: utf-8 -*-
"""coffee30_skeletons.py — 咖啡故事版单人 OpenPose 骨架(COCO-18 标准配色, 同 820 _zpose_skeleton 规范)
生成: sk_portrait.png 正面端坐(人物参考图用) / sk_window.png 坐起捧物(微笑举杯关键帧用) / sk_blank.png 空白(静物测试用)
"""
from PIL import Image, ImageDraw
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "output/script_first/coffee30_story_v1/ref"
OUT.mkdir(parents=True, exist_ok=True)

W, H = 1200, 1600
S = 1.25  # 坐标系按 960x1280 维护, 绘制等比放大

LIMBS = [
    (1, 2, (255, 0, 0)), (1, 5, (255, 85, 0)), (2, 3, (255, 170, 0)), (3, 4, (255, 255, 0)),
    (5, 6, (170, 255, 0)), (6, 7, (85, 255, 0)), (1, 8, (0, 255, 0)), (8, 9, (0, 255, 85)),
    (9, 10, (0, 255, 170)), (1, 11, (0, 255, 255)), (11, 12, (0, 170, 255)), (12, 13, (0, 85, 255)),
    (1, 0, (0, 0, 255)), (0, 14, (85, 0, 255)), (0, 15, (170, 0, 255)), (14, 16, (255, 0, 255)),
    (15, 17, (255, 0, 170)),
]

def draw_person(pts, path):
    img = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(img)
    p = {k: (round(x * S), round(y * S)) for k, (x, y) in pts.items()}
    for i, j, c in LIMBS:
        if i in p and j in p:
            d.line([p[i], p[j]], fill=c, width=12)
    for k, (x, y) in p.items():
        r = 9 if k >= 14 else 11
        color = (255, 64, 64) if k < 14 else (153, 0, 102)
        d.ellipse([x - r, y - r, x + r, y + r], fill=color)
    img.save(path)
    print("saved", path)

# ---- 正面端坐, 双手合于腿上(人物参考图: 面部+上身为主, 微不对称避免僵硬) ----
portrait = {
    0: (482, 242), 1: (480, 332),
    2: (398, 356), 5: (562, 358),
    3: (362, 484), 6: (598, 482),
    4: (444, 572), 7: (518, 574),
    8: (436, 642), 11: (526, 644),
    9: (418, 832), 12: (542, 834),
    10: (428, 1044), 13: (534, 1046),
    14: (456, 226), 15: (508, 224),
    16: (414, 236), 17: (548, 234),
}

# ---- 坐起捧物: 头微转向右侧窗方向, 双手抬至胸前捧杯 ----
window = {
    0: (498, 238), 1: (488, 330),
    2: (402, 352), 5: (566, 356),
    3: (368, 470), 6: (604, 468),
    4: (452, 512), 7: (536, 508),
    8: (440, 646), 11: (530, 648),
    9: (424, 836), 12: (548, 838),
    10: (434, 1048), 13: (540, 1050),
    14: (474, 222), 15: (524, 218),
    16: (432, 232), 17: (564, 228),
}

draw_person(portrait, OUT / "sk_portrait.png")
draw_person(window, OUT / "sk_window.png")

# ---- 空白骨架: 静物测试(无关键点 → controlnet 不注入人物) ----
Image.new("RGB", (W, H), (0, 0, 0)).save(OUT / "sk_blank.png")
print("saved", OUT / "sk_blank.png")

# ---- 横版(16:9 视频关键帧用): 1600x1200, 姿态坐标系等比缩放并水平居中 ----
WL, HL = 1600, 1200
SL = 0.9375          # 1200/1280
XOFF = (WL - 960 * SL) / 2

def draw_person_landscape(pts, path):
    img = Image.new("RGB", (WL, HL), (0, 0, 0))
    d = ImageDraw.Draw(img)
    p = {k: (round(x * SL + XOFF), round(y * SL)) for k, (x, y) in pts.items()}
    for i, j, c in LIMBS:
        if i in p and j in p:
            d.line([p[i], p[j]], fill=c, width=12)
    for k, (x, y) in p.items():
        r = 9 if k >= 14 else 11
        color = (255, 64, 64) if k < 14 else (153, 0, 102)
        d.ellipse([x - r, y - r, x + r, y + r], fill=color)
    img.save(path)
    print("saved", path)

draw_person_landscape(window, OUT / "sk_window_l.png")
Image.new("RGB", (WL, HL), (0, 0, 0)).save(OUT / "sk_blank_l.png")
print("saved", OUT / "sk_blank_l.png")
