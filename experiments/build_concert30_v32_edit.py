# -*- coding: utf-8 -*-
"""Assemble concert30 v3 final edit: complete story, generated-and-repaired both roles,
genuine master audio, watermark-safe crops on H-ref plates.

Timeline (film time):
  S1 0.00-4.90  real Nanchang opening
  S2 4.90-6.35  real singer closeup -> 6.35-9.85 repaired girl spotlight (dark crowd)
  S3 9.85-14.90 repaired girl crowd-push
  S4 14.90-19.30 repaired two-person pull-up (story complete)
  S5 19.30-24.85 repaired two-person bouquet raise
  S6 24.85-29.05 repaired photo-together strobes -> 29.05-30.00 real final downbeat
Audio: genuine master 313.0-343.0s.
"""
from __future__ import annotations
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output'/'concert30_hcy_flowers_v2'
REAL = OUT/'real'; REP = OUT/'repaired'
FINAL = OUT/'concert30_hcy_flowers_v32_master.mp4'

def run(cmd):
    print(' '.join(str(c) for c in cmd[:8]), '...', flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: print(r.stderr[-3000:]); sys.exit(r.returncode)

NORM = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=30,format=yuv420p"
TAIL = "crop=1232:696:56:0,scale=1920:1080,setsar=1,fps=30,format=yuv420p"
# H-ref plates inherit official-video overlays (1344x768 plate coords, vision-located 2026-09-15):
# TL studio+bilibili watermark / TR triangle logo -> blur-cover: crop corner, heavy boxblur, overlay back
# (keeps local luminance so glow-stick areas stay plausible; text becomes unreadable haze);
# BC lyric subtitle -> crop band; 1232x696 is exact 16:9 so scale is clean.
BLUR = 'boxblur=luma_radius=22:luma_power=2:chroma_radius=22:chroma_power=2'

GRADE = "eq=contrast=1.05:saturation=1.10:brightness=0.005"

def seg(idx, t0, dur, watermark_safe=False, extra=''):
    head = f"trim=start={t0}:duration={dur},setpts=PTS-STARTPTS"
    tail = (TAIL if watermark_safe else NORM)
    if extra: tail += f',{extra}'
    if not watermark_safe:
        return [f'[{idx}:v]{head},{tail},{GRADE}[v{idx}]']
    s1, s2 = f'a{idx}', f'b{idx}'
    return [
        f'[{idx}:v]{head},split[{s1}][{s2}]',
        f'[{s1}]crop=264:92:18:6,{BLUR}[{idx}tl]',
        f'[{s2}][{idx}tl]overlay=18:6[{idx}t1]',
        f'[{idx}t1]split[{s1}][{s2}]',
        f'[{s1}]crop=248:118:1094:4,{BLUR}[{idx}tr]',
        f'[{s2}][{idx}tr]overlay=1094:4[{idx}t2]',
        f'[{idx}t2]{tail},{GRADE}[v{idx}]',
    ]

def main():
    inputs = [
        REAL/'S1_real_processed.mp4',                                  # 0
        REAL/'inserts'/'official_096_100_singing.mp4',                 # 1
        REP/'S2v6ab_rt.mp4',                                       # 2
        REP/'S3ab_rt.mp4',                                       # 3
        REP/'S4ab_repaired.mp4',                                       # 4
        REP/'S5ab_ref01_rt.mp4',                                       # 5
        REP/'S6v32_repaired.mp4',                                       # 6
        REAL/'inserts'/'official_128_132_openmouth.mp4',               # 7
        REAL/'master_313_343.wav',                                     # 8
    ]
    cmd = ['ffmpeg','-y','-v','error']
    for p in inputs: cmd += ['-i', str(p)]
    f = []
    f += seg(0, 0, 4.90)                                   # S1 real
    f += seg(1, 0.2, 1.45)                                 # real singer closeup
    f += seg(2, 1.20, 3.50, watermark_safe=True)           # girl spotlight dark (skip weak open)
    f += seg(3, 0.10, 5.05)                                # crowd push
    f += seg(4, 0.00, 4.40, watermark_safe=True)           # pull-up
    f += seg(5, 0.00, 5.55, watermark_safe=True)           # bouquet raise
    f += seg(6, 0.00, 4.20, watermark_safe=True)           # photo strobes
    f += seg(7, 0.4, 0.95)                                 # real final downbeat
    f.append('[v0][v1][v2][v3][v4][v5][v6][v7]concat=n=8:v=1:a=0[vout]')
    f.append('[8:a]atrim=start=0:duration=30,asetpts=PTS-STARTPTS,alimiter=limit=0.95[aout]')
    cmd += ['-filter_complex', ';'.join(f), '-map', '[vout]', '-map', '[aout]',
            '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k',
            '-movflags', '+faststart', str(FINAL)]
    run(cmd)
    probe = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(FINAL)], capture_output=True, text=True)
    print(probe.stdout)
    print(f'[edit] {FINAL} {FINAL.stat().st_size//1024//1024}MB')

if __name__ == '__main__': main()
