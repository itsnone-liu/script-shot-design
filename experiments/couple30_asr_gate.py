# -*- coding: utf-8 -*-
"""couple30 ASR intelligibility gate: per-line CER on the final master.

Extracts each dialogue line's time window from the mixed master (segment
offsets from actual video durations), transcribes with faster-whisper (zh),
computes char error rate vs the authoritative dialogue.json text.

Gate: per-line CER <= 0.15 (character-normalized, punctuation stripped).
Usage: python -X utf8 experiments/couple30_asr_gate.py <master.mp4>
"""
from __future__ import annotations

import difflib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")  # CN mirror

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "creative_v2" / "couple30_v1"
AUD = OUT / "audio"


def dur(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return float(r.stdout.strip())


T2S = str.maketrans("沒曬陽簾這後個時還來對說過發現吧嗎們裡點鐘幾關開樣麼0123456789",
                    "没晒阳帘这后个时还来对说过发现吧吗们里点钟几开关样么零一二三四五六七八九")


def norm(s: str) -> str:
    s = s.translate(T2S)
    s = re.sub(r"[^\u4e00-\u9fffa-z0-9]", "", s.lower())
    return s


def main() -> int:
    master = Path(sys.argv[1])
    m = re.search(r"master_v(\d+)", master.name)
    arm = f"v{m.group(1)}" if m else ("yi" if "_yi" in master.name else "jia")
    rep = OUT / "repaired"
    if arm == "jia":  # mirror couple30_mix.py source choice
        a_cands = [rep / "A_repaired.mp4",
                   ROOT / "output" / "creative_v2" / "couple30_v1" / "shots" / "C30_A_T1_00.mp4"]
    elif arm in ("v21", "v22", "v23"):
        a_cands = [rep / "A_regen3_00.mp4"]
    else:
        a_cands = [rep / "A_regen3_00.mp4", rep / "A_regen2.mp4",
                   rep / "A_regen_00.mp4", rep / "A_repaired.mp4"]
    v2x = arm in ("v21", "v22", "v23", "v24", "v25", "v26", "v27", "v28")
    b_c = ([rep / "B_regen5_repaired.mp4", rep / "B_regen5_00.mp4",
            rep / "B_regen4_repaired.mp4", rep / "B_regen4_00.mp4",
            rep / "B_regen3_repaired.mp4", rep / "B_regen3_00.mp4",
            rep / "B_regen2_repaired.mp4", rep / "B_regen_repaired.mp4",
            rep / "B_regen_00.mp4"] if v2x else [rep / "B_repaired.mp4"])
    c_c = ([rep / "C_regen2_repaired.mp4", rep / "C_regen2_00.mp4",
            rep / "C_regen_repaired.mp4", rep / "C_regen_00.mp4"]
           if v2x else [rep / "C_lipsync_00.mp4", rep / "C_repaired.mp4"])
    segs = {"A": a_cands,
            "B": [next(p for p in b_c if p.exists())],
            "C": [next(p for p in c_c if p.exists())]}
    seg_dur = {}
    for k, cands in segs.items():
        seg_dur[k] = next(dur(c) for c in cands if c.exists())
    off = {"A": 0.0, "B": seg_dur["A"], "C": seg_dur["A"] + seg_dur["B"]}
    print(f"arm={arm} segment offsets:", {k: round(v, 2) for k, v in off.items()})

    from faster_whisper import WhisperModel
    local = ROOT / "output" / ".models" / "whisper-small"
    model = WhisperModel(str(local) if (local / "model.bin").exists() else "small",
                         device="cpu", compute_type="int8")

    tl_name = ("timeline_v24.json" if arm in ("v24", "v25", "v26", "v27",
                                              "v28")
               else "timeline.json")
    tl = json.loads((AUD / tl_name).read_text(encoding="utf-8"))
    rows, fails = [], 0
    tmp = Path(tempfile.gettempdir()) / "c30_asr.wav"
    for seg, lines in tl.items():
        for ln in lines:
            t0 = max(0.0, off[seg] + ln["start"] - 0.25)
            t1 = off[seg] + ln["start"] + ln["dur"] + 0.45
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t0:.3f}",
                            "-to", f"{t1:.3f}", "-i", str(master), "-vn",
                            "-c:a", "pcm_s16le", "-ar", "16000", "-ac", "1", str(tmp)],
                           check=True)
            segs_out, _ = model.transcribe(str(tmp), language="zh", beam_size=5,
                                           vad_filter=False)
            hyp = norm("".join(x.text for x in segs_out))
            ref = norm(ln["text"])
            cer = 1.0 - difflib.SequenceMatcher(None, ref, hyp).ratio() if ref else 1.0
            ok = cer <= 0.15
            fails += (not ok)
            rows.append((ln["id"], ln["speaker"], round(cer, 3), "PASS" if ok else "FAIL",
                         ln["text"], hyp[:30]))
            print(f"[{ln['id']}] {ln['speaker']} CER={cer:.3f} {'PASS' if ok else 'FAIL'} "
                  f"ref={ln['text']} hyp={hyp}")
    print(f"\n{len(rows)-fails}/{len(rows)} lines pass (CER<=0.15)")
    (OUT / "asr_gate_report.json").write_text(
        json.dumps([{"id": r[0], "speaker": r[1], "cer": r[2], "verdict": r[3],
                     "ref": r[4], "hyp": r[5]} for r in rows], ensure_ascii=False, indent=1),
        encoding="utf-8")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
