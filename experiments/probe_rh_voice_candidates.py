"""Probe RH webapp details for top voice-line workflow candidates."""
from __future__ import annotations

import json
import sys

sys.path.insert(0, r"D:\qjcNetDiskDownload\deepseek-harness\project\820")
import rh_client as rh  # noqa: E402

CANDS = {
    "2095531397845889025": "对口型音频驱动-首尾帧-MiniMax H3数字人",
    "2097512820928790529": "对口型MinimaxH3音频驱动数字人单人版（ultra版）",
    "2076998668398784513": "LatentSync1.6数字人基础版",
    "2086650291638005762": "对口型-视频对口型-不限视频长度-高清优化版",
    "2086650599655108610": "对口型-多人数字人对口型-高清版本",
    "2095429364939161601": "音频驱动数字人|minimaxH3语音口型同步|文/图生视频",
    "2093959907870511105": "音色克隆IndexTTS2",
}

out = {}
for wa, name in CANDS.items():
    try:
        simp = rh.webapp_simple(wa)
        wf = str(simp.get("workflowId") or "")
        nodes = simp.get("inputNodes") or []
        desc = {
            "name": name,
            "webapp": wa,
            "workflowId": wf,
            "inputs": [
                {"id": n.get("id"), "name": n.get("nodeName") or n.get("name"),
                 "type": n.get("fileType") or n.get("type"),
                 "label": (n.get("description") or "")[:80]}
                for n in nodes
            ],
        }
        out[wa] = desc
        print(f"== {name}\n   webapp={wa} wf={wf}")
        for n in desc["inputs"]:
            print(f"   [{n['type']}] {n['name']} (#{n['id']}): {n['label']}")
    except Exception as exc:
        print(f"== {name}\n   FAIL {str(exc)[:100]}")
        out[wa] = {"name": name, "error": str(exc)[:200]}

dest = r"D:\qjcNetDiskDownload\deepseek-harness\project\821\output\research_voice\rh_voice_candidates.json"
with open(dest, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("saved ->", dest)
