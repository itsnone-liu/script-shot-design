# -*- coding: utf-8 -*-
"""Assemble concert30 v2 final edit: hybrid plates + real footage + genuine master audio.

Timeline (film time, seconds):
  S1 0.00-4.90  real processed Nanchang cut
  S2 4.90-9.85  real singer closeup (1.45) -> repaired girl spotlight plate (3.50)
  S3 9.85-14.90 sprint plate 1.6x (3.10) -> real crowd/reach insert (1.10) -> sprint tail (0.85)
  S4 14.90-19.30 handoff plate (4.40)
  S5 19.30-24.85 wide two-shot plate (3.55) -> real energetic singer (2.00)
  S6 24.85-30.00 strobe plate (3.60) -> real arena/singer final downbeat (1.55)
Audio: genuine master 313.0-343.0 over the whole film; plate audio dropped.
Output: 1920x1080 30fps h264 + aac.
"""
from __future__ import annotations
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output'/'concert30_hcy_flowers_v2'
REAL = OUT/'real'; SHOTS = OUT/'shots'; REP = OUT/'repaired'
FINAL = OUT/'concert30_hcy_flowers_v2_master.mp4'

def run(cmd):
    print(' '.join(str(c) for c in cmd), flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: print(r.stderr[-3000:]); sys.exit(r.returncode)

NORM = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=30,format=yuv420p"
GRADE = "eq=contrast=1.06:saturation=1.12:brightness=0.01"

def seg(src: Path, t0: float, dur: float, speed: float = 1.0, extra: str = "") -> str:
    parts = [f"[{src.stem}]"] if False else []
    filt = f"trim=start={t0}:duration={dur},setpts=PTS-STARTPTS"
    if speed != 1.0: filt += f",setpts=PTS/{speed}"
    filt += f",{NORM}"
    if extra: filt += f",{extra}"
    filt += f",{GRADE}"
    return filt

def main():
    inputs = [
        ('s1', REAL/'S1_real_processed.mp4'),
        ('s2g', REP/'S2girl_24fps.mp4'),
        ('s3', SHOTS/'S3_v4_ACCEPT.mp4'),
        ('s4', SHOTS/'S4_v1_ACCEPT.mp4'),
        ('s5', SHOTS/'S5_v1_ACCEPT.mp4'),
        ('s6', SHOTS/'S6_00.mp4'),
        ('r_point', REAL/'inserts'/'official_096_100_singing.mp4'),
        ('r_reach', REAL/'inserts'/'theseus_240_244_rightface.mp4'),
        ('r_energy', REAL/'inserts'/'weird_218_222_energetic.mp4'),
        ('r_final', REAL/'inserts'/'official_128_132_openmouth.mp4'),
        ('r_arena', REAL/'S1_real_313_317.9.mp4'),
        ('aud', REAL/'master_313_343.wav'),
    ]
    cmd = ['ffmpeg','-y','-v','error']
    for _, p in inputs: cmd += ['-i', str(p)]

    f = []
    # S1 real 0.00-4.90 (5.08 source, trim tail)
    f.append(f"[0:v]{seg(REAL/'S1_real_processed.mp4',0,4.90)}[v0]")
    # S2: real singer 1.45 + girl spotlight 3.50 (5.125 source)
    f.append(f"[6:v]{seg(REAL/'inserts'/'official_096_100_singing.mp4',0.2,1.45)}[v1]")
    f.append(f"[1:v]{seg(REP/'S2girl_24fps.mp4',0.4,3.50)}[v2]")
    # S3: sprint 1.6x 3.10 + reach insert 1.10 + sprint tail 0.85 (offset 3.10*1.6=4.96 in source)
    f.append(f"[2:v]{seg(SHOTS/'S3_v4_ACCEPT.mp4',0.5,3.10,1.6)}[v3]")
    f.append(f"[7:v]{seg(REAL/'inserts'/'theseus_240_244_rightface.mp4',0.3,1.10)}[v4]")
    f.append(f"[2:v]{seg(SHOTS/'S3_v4_ACCEPT.mp4',4.3,0.85,1.3)}[v5]")
    # S4 handoff full 4.40
    f.append(f"[3:v]{seg(SHOTS/'S4_v1_ACCEPT.mp4',0,4.40)}[v6]")
    # S5: wide 4.22 + energetic singer 2.00
    f.append(f"[4:v]{seg(SHOTS/'S5_v1_ACCEPT.mp4',0.6,4.22)}[v7]")
    f.append(f"[8:v]{seg(REAL/'inserts'/'weird_218_222_energetic.mp4',0.5,2.00)}[v8]")
    # S6: strobe 4.60 + arena 0.60 + final downbeat 0.95
    f.append(f"[5:v]{seg(SHOTS/'S6_00.mp4',0.3,4.60)}[v9]")
    f.append(f"[9:v]{seg(REAL/'S1_real_313_317.9.mp4',3.9,0.60)}[v10]")
    f.append(f"[9:v]{seg(REAL/'inserts'/'official_128_132_openmouth.mp4',0.4,0.95)}[v11]")
    f.append("[v0][v1][v2][v3][v4][v5][v6][v7][v8][v9][v10][v11]concat=n=12:v=1:a=0[vout]")
    aud = "[10:a]atrim=start=0:duration=30,asetpts=PTS-STARTPTS,alimiter=limit=0.95[aout]"
    f.append(aud)
    fc = ';'.join(f)
    cmd += ['-filter_complex', fc, '-map', '[vout]', '-map', '[aout]',
            '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k',
            '-movflags', '+faststart', str(FINAL)]
    run(cmd)
    probe = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration:stream=width,height,r_frame_rate,codec_type','-of','json',str(FINAL)], capture_output=True, text=True)
    print(probe.stdout)
    print(f'[edit] {FINAL} {FINAL.stat().st_size//1024//1024}MB')

if __name__ == '__main__': main()
