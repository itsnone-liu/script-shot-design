# -*- coding: utf-8 -*-
"""couple30 final mix: video concat + dialogue track + native ambience bed.

Arms:
  甲 (jia)  A_repaired.mp4  — identity-repaired original A (repair chain)
  乙 (yi)   A_regen_00.mp4  — audio-driven regenerated A (first/last frame)
Both use B_repaired.mp4 + C_lipsync_00.mp4 (fallback C_repaired.mp4).

Audio = segA/segB/segC dialogue tracks (35s) + ambience bed extracted from the
original takes (lowpassed 400Hz, -19dB — keeps bedding/room rumble, drops the
gibberish speech band). Loudnorm -16 LUFS. Output: couple30_v2_master_{arm}.mp4
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "creative_v2" / "couple30_v1"
REP = OUT / "repaired"
AUD = OUT / "audio"
SHOTS = ROOT / "output" / "creative_v2" / "couple30_v1" / "shots"


def dur(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return float(r.stdout.strip())


def run(cmd: list[str]) -> None:
    r = subprocess.run(cmd)
    if r.returncode:
        raise SystemExit(f"cmd failed: {' '.join(cmd[:6])}...")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm",
                    choices=["jia", "yi", "v21", "v22", "v23", "v24", "v25",
                             "v26", "v27", "v28"],
                    required=True)
    args = ap.parse_args()

    # 甲 arm = repair route; ReActor cannot lock A's top-down W (probe FAIL_BOTH),
    # so甲 falls back to the original A_T1 take — that IS the honest 甲 baseline.
    if args.arm == "jia":
        a_src = next((p for p in [REP / "A_repaired.mp4",
                                  ROOT / "output" / "creative_v2" / "couple30_v1" /
                                  "shots" / "C30_A_T1_00.mp4"]
                      if p.exists()), None)
    elif args.arm in ("v21", "v22", "v23", "v24", "v25", "v26", "v27",
                      "v28"):
        # v2.1+: ALL segments audio-driven regen (lipsync by construction)
        a_src = REP / "A_regen3_00.mp4"
    else:
        a_src = next((p for p in [REP / "A_regen3_00.mp4", REP / "A_regen2.mp4",
                                  REP / "A_regen_00.mp4", REP / "A_repaired.mp4"]
                      if p.exists()), None)
    if not a_src or not a_src.exists():
        raise SystemExit(f"A source missing for arm {args.arm}")
    if args.arm in ("v21", "v22", "v23", "v24", "v25", "v26", "v27", "v28"):
        b_c = ([REP / "B_regen5_repaired.mp4", REP / "B_regen5_00.mp4"]
               if args.arm == "v28" else
               [REP / "B_regen4_repaired.mp4", REP / "B_regen4_00.mp4"]
               if args.arm == "v27" else
               [REP / "B_regen3_repaired.mp4", REP / "B_regen3_00.mp4"]
               if args.arm in ("v24", "v25", "v26") else
               [REP / "B_regen2_repaired.mp4", REP / "B_regen2_00.mp4"]
               if args.arm == "v23" else
               [REP / "B_regen_repaired.mp4", REP / "B_regen_00.mp4"])
        c_c = ([REP / "C_regen2_repaired.mp4", REP / "C_regen2_00.mp4"]
               if args.arm in ("v24", "v25", "v26", "v27", "v28") else
               [REP / "C_regen_repaired.mp4", REP / "C_regen_00.mp4"])
        b_src = next((p for p in b_c if p.exists()), None)
        c_src = next((p for p in c_c if p.exists()), None)
        if not b_src or not c_src:
            raise SystemExit("v2x needs B/C regen outputs")
        vids = [a_src, b_src, c_src]
    else:
        c_src = (REP / "C_lipsync_00.mp4")
        if not c_src.exists():
            print("C_lipsync missing; falling back to C_repaired (no W lipsync on L10)")
            c_src = REP / "C_repaired.mp4"
        vids = [a_src, REP / "B_repaired.mp4", c_src]
    for v in vids:
        print(f"  {v.name} {dur(v):.2f}s")

    # 1) video concat (uniform re-encode)
    total = sum(dur(v) for v in vids)
    vc = OUT / f"v2_{args.arm}_video.mp4"
    if not vc.exists():
        cmd = ["ffmpeg", "-y", "-v", "error"]
        for v in vids:
            cmd += ["-i", str(v)]
        # uniform 672x896: cover-scale + center-crop (i2v regen may return 736x1280)
        f = ";".join(f"[{i}:v]scale=672:896:force_original_aspect_ratio=increase,"
                     f"crop=672:896,setsar=1[v{i}]" for i in range(len(vids)))
        cin = "".join(f"[v{i}]" for i in range(len(vids)))
        run(cmd + ["-filter_complex", f"{f};{cin}concat=n={len(vids)}:v=1:a=0[v]", "-map", "[v]",
                   "-c:v", "libx264", "-preset", "slow", "-crf", "16",
                   "-pix_fmt", "yuv420p", "-an", str(vc)])
    print("video ->", vc)

    # 2) dialogue track, aligned to THIS arm's actual video durations
    #    (segA_dialogue is 15s fixed; 甲-arm A take is 14.375s -> trim/pad per arm)
    seg_audio = {"A": AUD / "segA_dialogue.wav", "B": AUD / "segB_dialogue.wav",
                 "C": AUD / "segC_dialogue.wav"}
    if args.arm == "v28":
        # v2.8: ORIGINAL native laugh performance overlays a video regen'd TO
        # that exact audio (driving track = same laugh), so rhythm matches by
        # construction; dialogue layer = clean TTS only, laugh lives in bed.
        seg_audio["B"] = AUD / "segB_l07.wav"
        seg_audio["C"] = AUD / "segC_perf.wav"
        print("v28 B L07-only + C perf ->", seg_audio["B"], seg_audio["C"])
    elif args.arm == "v27":
        # v2.7: laughter HARVESTED from the regen take's own audio track
        # (jointly generated with its choreography -> rhythm-matched).
        # dialogue layer: clean TTS only; laugh layer lives in the bed.
        seg_audio["B"] = AUD / "segB_l07.wav"
        seg_audio["C"] = AUD / "segC_perf.wav"
        print("B L07-only + C perf ->", seg_audio["B"], seg_audio["C"])
    elif args.arm in ("v24", "v25", "v26"):
        # v2.4+: script-logic redesign — B perf3 (L07@0.3 + laughter-only turn),
        # C perf (L08 moved to C head before L09)
        # v26: B perf4 — laughter welded to the visual laughing span/flip beat
        seg_audio["B"] = (AUD / "segB_perf4.wav" if args.arm == "v26"
                          else AUD / "segB_perf3.wav")
        seg_audio["C"] = AUD / "segC_perf.wav"
        print("B perf + C perf ->", seg_audio["B"], seg_audio["C"])
    elif args.arm == "v23":
        # v2.3: B = effortful regen2; audio = performance track v2
        seg_audio["B"] = AUD / "segB_perf2.wav"
        print("B perf2 (effort delivery) ->", seg_audio["B"])
    elif args.arm == "v22":
        # B performance = dialogue + original turn-laughter placed at 6.15s
        # (she protests L08 until 6.15s, then breaks into laughter at the end
        #  tangle; native burst 2.68-3.90s identified as laughter by envelope)
        laugh = AUD / "laugh_B.wav"
        if not laugh.exists():
            run(["ffmpeg", "-y", "-v", "error", "-ss", "2.68", "-to", "3.90",
                 "-i", str(AUD / "native_B.wav"),
                 "-af", "afade=t=in:d=0.04,afade=t=out:st=1.10:d=0.14,"
                        "aresample=44100,pan=stereo|c0=c0|c1=c0",
                 "-c:a", "pcm_s16le", str(laugh)])
        perf_b = AUD / "segB_perf.wav"
        if not perf_b.exists():
            run(["ffmpeg", "-y", "-v", "error",
                 "-i", str(seg_audio["B"]), "-i", str(laugh),
                 "-filter_complex",
                 "[1:a]volume=-6dB,adelay=6150|6150[l];"
                 "[0:a][l]amix=inputs=2:normalize=0,dynaudnorm=f=300:g=15[m]",
                 "-map", "[m]", "-c:a", "pcm_s16le", str(perf_b)])
        seg_audio["B"] = perf_b
        print("B perf (dialogue+laugh@6.15s) ->", perf_b)
    dlg = OUT / f"v2_{args.arm}_dialogue.wav"
    if not dlg.exists():
        cmd = ["ffmpeg", "-y", "-v", "error"]
        for v, k in zip(vids, ["A", "B", "C"]):
            cmd += ["-i", str(seg_audio[k])]
        flt = ";".join(f"[{i}:a]aresample=44100,apad=whole_dur={dur(v):.3f},"
                       f"atrim=0:{dur(v):.3f}[a{i}]" for i, v in enumerate(vids))
        cin = "".join(f"[a{i}]" for i in range(len(vids)))
        # v25: subtle small-room slap on the whole dialogue track so the dry
        # TTS lines share acoustic space with the native laughter clip.
        # NOTE: aecho=in_gain:out_gain:delays:decays — gains <1 attenuate the
        # dry path (0.5*0.35 = -15dB); keep dry at unity, wet stays subtle.
        room = (",aecho=1:1:21|33:0.16|0.10"
                if args.arm in ("v25", "v26", "v27", "v28") else "")
        run(cmd + ["-filter_complex",
                   f"{flt};{cin}concat=n={len(vids)}:v=0:a=1{room}[a]",
                   "-map", "[a]", "-c:a", "pcm_s16le", str(dlg)])
    print("dialogue ->", dlg)

    # 3) ambience bed (aligned by segment durations)
    #    v21: atmos = native audio minus speech spans (laughter/BGM kept)
    bed = OUT / f"v2_{args.arm}_bed.wav"
    if not bed.exists():
        if args.arm == "v28":
            # v28: B bed = ORIGINAL native laugh performance + room tone;
            # A/C = synthetic room tone
            beds = [AUD / "bed_room_A.wav", AUD / "bed_B_orig.wav",
                    AUD / "bed_room_C.wav"]
            atmos = [p if p.exists() else beds[0] for p in beds]
            cmd = ["ffmpeg", "-y", "-v", "error"]
            for p in atmos:
                cmd += ["-i", str(p)]
            flt = ";".join(f"[{i}:a]aresample=44100,"
                           f"apad=whole_dur={dur(v):.3f},"
                           f"atrim=0:{dur(v):.3f}[b{i}]" for i, v in enumerate(vids))
            cin = "".join(f"[b{i}]" for i in range(len(vids)))
            run(cmd + ["-filter_complex", f"{flt};{cin}concat=n={len(vids)}:v=0:a=1[a]",
                       "-map", "[a]", "-c:a", "pcm_s16le", str(bed)])
        elif args.arm == "v26":
            # v26: ALL beds synthetic room tone — native-derived beds kept
            # leaking speech murmur (150-750Hz fundamentals survive 800Hz LP)
            beds = [AUD / "bed_room_A.wav", AUD / "bed_room_B.wav",
                    AUD / "bed_room_C.wav"]
            atmos = [p if p.exists() else beds[0] for p in beds]
            cmd = ["ffmpeg", "-y", "-v", "error"]
            for p in atmos:
                cmd += ["-i", str(p)]
            flt = ";".join(f"[{i}:a]aresample=44100,"
                           f"apad=whole_dur={dur(v):.3f},"
                           f"atrim=0:{dur(v):.3f}[b{i}]" for i, v in enumerate(vids))
            cin = "".join(f"[b{i}]" for i in range(len(vids)))
            run(cmd + ["-filter_complex", f"{flt};{cin}concat=n={len(vids)}:v=0:a=1[a]",
                       "-map", "[a]", "-c:a", "pcm_s16le", str(bed)])
        elif args.arm == "v25":
            # v25: B bed = neutral synthetic room tone — atmos_B was derived
            # from an ALL-laughter native track; even lowpassed it leaked a
            # muffled "ghost laugh" under the whole segment.
            beds = [AUD / "atmos_A2.wav", AUD / "bed_B_room.wav",
                    AUD / "atmos_C2.wav"]
            atmos = [p if p.exists() else beds[0] for p in beds]
            cmd = ["ffmpeg", "-y", "-v", "error"]
            for p in atmos:
                cmd += ["-i", str(p)]
            flt = ";".join(f"[{i}:a]aresample=44100,"
                           f"apad=whole_dur={dur(v):.3f},"
                           f"atrim=0:{dur(v):.3f}[b{i}]" for i, v in enumerate(vids))
            cin = "".join(f"[b{i}]" for i in range(len(vids)))
            run(cmd + ["-filter_complex", f"{flt};{cin}concat=n={len(vids)}:v=0:a=1[a]",
                       "-map", "[a]", "-c:a", "pcm_s16le", str(bed)])
        elif args.arm in ("v21", "v22", "v23", "v24"):
            beds = ([AUD / "atmos_A2.wav", AUD / "atmos_B2.wav",
                     AUD / "atmos_C2.wav"] if args.arm == "v24"
                    else [AUD / "atmos_A.wav", AUD / "atmos_B.wav",
                          AUD / "atmos_C.wav"])
            atmos = [p if p.exists() else beds[0] for p in beds]
            cmd = ["ffmpeg", "-y", "-v", "error"]
            for p in atmos:
                cmd += ["-i", str(p)]
            # v22+: B bed = pure low rumble (laughter lives in performance track
            # now; native B bursts would desync + overlap dialogue).
            # v24: all beds pre-lowpassed at build time (ghost-speech kill).
            bflt = ("" if args.arm == "v24" else
                    ",lowpass=f=500,volume=-4dB" if args.arm in ("v22", "v23")
                    else "")
            flt = ";".join(f"[{i}:a]aresample=44100{bflt if i == 1 else ''},"
                           f"apad=whole_dur={dur(v):.3f},"
                           f"atrim=0:{dur(v):.3f}[b{i}]" for i, v in enumerate(vids))
            cin = "".join(f"[b{i}]" for i in range(len(vids)))
            run(cmd + ["-filter_complex", f"{flt};{cin}concat=n={len(vids)}:v=0:a=1[a]",
                       "-map", "[a]", "-c:a", "pcm_s16le", str(bed)])
        else:
            takes = [SHOTS / "C30_A_T1_00.mp4", SHOTS / "C30_B_T2_00.mp4", SHOTS / "C30_C_T2_00.mp4"]
            cmd = ["ffmpeg", "-y", "-v", "error"]
            for t in takes:
                cmd += ["-t", f"{dur(t):.3f}", "-i", str(t)]
            f = "".join(f"[{i}:a]" for i in range(len(takes)))
            run(cmd + ["-filter_complex",
                       f"{f}concat=n=3:v=0:a=1,lowpass=f=400,volume=-19dB,"
                       f"aresample=44100,pan=stereo|c0=c0|c1=c1[a]",
                       "-map", "[a]", "-c:a", "pcm_s16le", str(bed)])
    print("bed ->", bed)

    # 4) final mix (dialogue + bed, pad/trim to video length, loudnorm)
    #    v25+: two-stage LINEAR loudnorm — dynamic mode rode gain up in the
    #    wordless B section and lifted the -42dB room tone to -18dB.
    dest = OUT / f"couple30_v2_master_{args.arm}.mp4"
    raw = OUT / f"v2_{args.arm}_mix_raw.wav"
    run(["ffmpeg", "-y", "-v", "error", "-i", str(dlg), "-i", str(bed),
         "-filter_complex",
         f"[0:a]aresample=44100,apad=whole_dur={total:.3f}[d];"
         f"[1:a]aresample=44100,apad=whole_dur={total:.3f}[b];"
         "[d][b]amix=inputs=2:normalize=0[a]",
         "-map", "[a]", "-c:a", "pcm_s16le", str(raw)])
    import json as _json
    import re as _re
    pr = subprocess.run(["ffmpeg", "-i", str(raw), "-af",
                         "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
                         "-f", "null", "-"], capture_output=True, text=True,
                        encoding="utf-8", errors="replace")
    blk = pr.stderr[pr.stderr.rfind("{"):]
    meas = _json.loads(blk[:blk.rfind("}") + 1])
    ln = (f"loudnorm=I=-16:TP=-1.5:LRA=11:linear=true:"
          f"measured_I={meas['input_i']}:measured_TP={meas['input_tp']}:"
          f"measured_LRA={meas['input_lra']}:"
          f"measured_thresh={meas['input_thresh']}")
    print("loudnorm linear:", ln)
    run(["ffmpeg", "-y", "-v", "error", "-i", str(vc), "-i", str(raw),
         "-af", ln, "-map", "0:v", "-map", "1:a", "-t", f"{total:.3f}",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(dest)])
    print("master ->", dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
