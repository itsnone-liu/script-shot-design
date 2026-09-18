# -*- coding: utf-8 -*-
"""C2 takes QA 抽帧拼图：每段一张 sheet（行=take，列=5%,25%,50%,75%,98% 帧）。"""
from __future__ import annotations
import io, json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "output" / "creative_v2" / "couple30_v1" / "shots"
QA = ROOT / "output" / "creative_v2" / "couple30_v1" / "qa"
QA.mkdir(parents=True, exist_ok=True)
SEGS = {"A": 3, "B": 4, "C": 3}
PCTS = [5, 25, 50, 75, 98]
TW, TH = 320, 426  # tile ~3:4

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise RuntimeError(r.stderr[-500:])

def duration_of(mp4: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(mp4)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())

for seg, n in SEGS.items():
    rows = []
    labels = []
    for take in range(1, n + 1):
        mp4 = SHOTS / f"C30_{seg}_T{take}_00.mp4"
        if not mp4.exists():
            continue
        dur = duration_of(mp4)
        tiles = []
        for p in PCTS:
            out = QA / f"f_{seg}_T{take}_{p}.jpg"
            run(["ffmpeg", "-y", "-v", "error", "-ss", f"{max(dur * p / 100 - 0.05, 0):.2f}",
                 "-i", str(mp4), "-frames:v", "1", "-q:v", "3", str(out)])
            if out.exists():
                im = Image.open(out).convert("RGB")
                im.thumbnail((TW, TH))
                tiles.append(im)
                out.unlink()
        if tiles:
            rows.append(tiles)
            labels.append(f"{seg} T{take}")
    if not rows:
        continue
    lw = 90
    sheet = Image.new("RGB", (lw + TW * len(PCTS), TH * len(rows) + 30), (16, 18, 22))
    d = ImageDraw.Draw(sheet)
    for c, p in enumerate(PCTS):
        d.text((lw + c * TW + 8, 6), f"{p}%", fill=(255, 209, 102))
    for r, (row, lab) in enumerate(zip(rows, labels)):
        d.text((8, r * TH + TH // 2), lab, fill=(126, 224, 138))
        for c, im in enumerate(row):
            sheet.paste(im, (lw + c * TW, 30 + r * TH))
    dest = QA / f"qa_sheet_{seg}.jpg"
    sheet.save(dest, quality=88)
    print("saved", dest.name, sheet.size)
