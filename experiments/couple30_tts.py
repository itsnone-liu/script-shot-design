# -*- coding: utf-8 -*-
"""couple30 TTS pipeline: 11 dialogue lines -> dry WAVs + measured durations.

Engines:
  edge     local edge-tts (free). Used for M lines v1 (zh-CN-YunxiNeural young male;
           no clone material for M yet). Can run without any RH dependency.
  indextts RH IndexTTS2 voice-clone webapp 2093959907870511105
           (node 11 emotion / node 4 text / node 10 ref audio). For W lines
           once the user's clone material arrives (10s+ dry female voice).

Usage:
  python -X utf8 experiments/couple30_tts.py --engine edge --speaker M
  python -X utf8 experiments/couple30_tts.py --engine indextts --speaker W --ref <clone.wav>
"""
from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIA = ROOT / "examples" / "couple30_v1" / "dialogue.json"
AUDIO = ROOT / "output" / "creative_v2" / "couple30_v1" / "audio"
TTS_STATE = AUDIO / "tts_state.json"

INDEXTTS_APP = "2093959907870511105"

# emotion -> edge-tts voice/rate/pitch (W = zh-CN-XiaoyiNeural young female v1
# — placeholder voice per user "先用随便什么语音"; upgrade to IndexTTS2 clone later)
EDGE_W = {
    "default": {"voice": "zh-CN-XiaoyiNeural", "rate": "+0%", "pitch": "+0Hz"},
    "bright": {"voice": "zh-CN-XiaoyiNeural", "rate": "+8%", "pitch": "+2Hz"},
    "coax": {"voice": "zh-CN-XiaoyiNeural", "rate": "-4%", "pitch": "+1Hz"},
    "smug": {"voice": "zh-CN-XiaoyiNeural", "rate": "+2%", "pitch": "+1Hz"},
    "muffled": {"voice": "zh-CN-XiaoyiNeural", "rate": "-6%", "pitch": "-1Hz"},
}
EMO_KEY_W = {
    "L01": "bright", "L03": "coax", "L05": "smug", "L08": "muffled", "L10": "coax",
}

# emotion -> edge-tts voice/rate/pitch (M = zh-CN-YunxiNeural)
EDGE_M = {
    "default": {"voice": "zh-CN-YunxiNeural", "rate": "+0%", "pitch": "+0Hz"},
    "mumble": {"voice": "zh-CN-YunxiNeural", "rate": "-12%", "pitch": "-2Hz"},
    "lazy": {"voice": "zh-CN-YunxiNeural", "rate": "-15%", "pitch": "-3Hz"},
    "laugh": {"voice": "zh-CN-YunxiNeural", "rate": "+6%", "pitch": "+2Hz"},
}
EMO_KEY_M = {  # per-line emotion -> edge style key
    "L02": "mumble", "L04": "lazy", "L06": "lazy",
    "L07": "laugh", "L11": "lazy",
}

# emotion hints for IndexTTS2 (node 11) per W line
EMO_TXT_W = {
    "L01": "轻快，带笑意的催促",
    "L03": "撒娇，劝说起身",
    "L05": "得意，带点威胁",
    "L08": "被子里笑骂，闷一点",
    "L10": "认命地笑，温柔",
}


def wav_seconds(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return round(float(r.stdout.strip()), 3)


def load_dia() -> dict:
    return json.loads(DIA.read_text(encoding="utf-8"))


def save_dia(d: dict) -> None:
    DIA.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


async def edge_line(text: str, style: dict, dest: Path) -> Path:
    import edge_tts
    com = edge_tts.Communicate(text, style["voice"], rate=style["rate"], pitch=style["pitch"])
    await com.save(str(dest))
    return dest


def run_edge(speaker: str) -> None:
    dia = load_dia()
    AUDIO.mkdir(parents=True, exist_ok=True)
    # A container uses the H3 max 15s; 6 turns need per-line absolute pacing
    # (measured: default pace ~20s, +15% flat ~17.8s). B/C keep style defaults.
    A_RATE = {"L01": "+18%", "L02": "+8%", "L03": "+22%", "L04": "+5%",
              "L05": "+18%", "L06": "+8%"}
    lines = [x for x in dia["lines"] if x["speaker"] == speaker]
    for ln in lines:
        dest = AUDIO / f"{ln['id']}.wav"
        if dest.exists():
            print(f"[{ln['id']}] exists {dest.name} ({wav_seconds(dest)}s)")
            continue
        if speaker == "M":
            style = dict(EDGE_M[EMO_KEY_M.get(ln["id"], "default")])
        else:
            style = dict(EDGE_W[EMO_KEY_W.get(ln["id"], "default")])
        if ln["segment"] == "A":
            style["rate"] = A_RATE[ln["id"]]
        asyncio.run(edge_line(ln["text"], style, dest))
        dur = wav_seconds(dest)
        ln["tts_seconds"] = dur
        ln["tts_file"] = str(dest)
        ln["tts_engine"] = "edge"
        print(f"[{ln['id']}] -> {dest.name} ({dur}s, {style['voice']} rate={style['rate']})")
    save_dia(dia)


def run_indextts(speaker: str, ref: Path) -> None:
    sys.path.insert(0, str(ROOT.parent / "820"))
    from experiments import rh_task
    if not ref.exists():
        raise SystemExit(f"clone ref not found: {ref}")
    dia = load_dia()
    AUDIO.mkdir(parents=True, exist_ok=True)
    key = rh_task.load_api_key()
    u_ref = rh_task.upload_file(key, ref)
    print(f"ref audio -> {u_ref}")
    lines = [x for x in dia["lines"] if x["speaker"] == speaker]
    for ln in lines:
        dest = AUDIO / f"{ln['id']}.wav"
        if dest.exists():
            print(f"[{ln['id']}] exists ({wav_seconds(dest)}s)")
            continue
        emo = EMO_TXT_W.get(ln["id"], "自然口语")
        node_info = [
            {"nodeId": "11", "fieldName": "prompt", "fieldValue": emo},
            {"nodeId": "4", "fieldName": "prompt", "fieldValue": ln["text"]},
            {"nodeId": "10", "fieldName": "audio", "fieldValue": u_ref},
        ]
        tid = rh_task.run_webapp(key, INDEXTTS_APP, node_info)
        print(f"[{ln['id']}] task {tid} emo={emo}", flush=True)
        out = rh_task.wait_task(key, tid, poll=8, max_wait=600)
        urls = rh_task.collect_file_urls(out)
        if not urls:
            raise RuntimeError(f"[{ln['id']}] no output")
        rh_task.download(urls[0], dest)
        dur = wav_seconds(dest)
        ln["tts_seconds"] = dur
        ln["tts_file"] = str(dest)
        ln["tts_engine"] = "indextts2"
        save_dia(dia)
        print(f"[{ln['id']}] -> {dest.name} ({dur}s)")
        time.sleep(2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["edge", "indextts"], required=True)
    ap.add_argument("--speaker", choices=["W", "M"], required=True)
    ap.add_argument("--ref", type=Path, default=None, help="clone reference wav for indextts")
    args = ap.parse_args()
    if args.engine == "edge":
        run_edge(args.speaker)
    else:
        if not args.ref:
            raise SystemExit("indextts needs --ref <clone.wav>")
        run_indextts(args.speaker, args.ref)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
