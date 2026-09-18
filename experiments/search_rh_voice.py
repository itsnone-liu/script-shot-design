"""821 voice-line research: search RH webapps for lip-sync / audio-drive / TTS workflows.

Read-only reuse of 820 rh_client (sys.path injected). Lists webapp id, title,
workflowId (via simple detail) for each keyword. No workflow copying.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, r"D:\qjcNetDiskDownload\deepseek-harness\project\820")
import rh_client as rh  # noqa: E402

KEYWORDS = [
    "对口型",
    "唇形同步",
    "口型",
    "LatentSync",
    "MuseTalk",
    "音频驱动",
    "数字人",
    "语音克隆",
    "音色克隆",
    "配音",
    "TTS",
]

def main() -> int:
    out = {}
    for kw in KEYWORDS:
        rows = []
        for page in range(1, 4):
            try:
                data = rh._post("/api/webapp/list",
                                {"size": 20, "current": page, "search": kw, "sort": ""})
                recs = data.get("records") or []
            except Exception as exc:
                print(f"[{kw}] list error: {str(exc)[:80]}")
                time.sleep(1)
                break
            if not recs:
                break
            for rec in recs:
                rows.append({"webapp": str(rec.get("id") or ""),
                             "title": rec.get("name") or ""})
            if len(recs) < 20:
                break
        out[kw] = rows
        print(f"== {kw}: {len(rows)} rows")
        for r in rows[:15]:
            print(f"   {r['webapp']}  {r['title'][:70]}")
        time.sleep(0.6)
    dest = Path(__file__).resolve().parent.parent / "output" / "research_voice" / "rh_voice_search.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"saved -> {dest}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
