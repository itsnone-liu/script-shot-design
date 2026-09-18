# -*- coding: utf-8 -*-
"""Dump full webapp simple-detail JSON for voice-line webapps (get nodeInfoList node ids)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, r"D:\qjcNetDiskDownload\deepseek-harness\project\820")
import rh_client as rh  # noqa: E402

APPS = {
    "indextts2_clone": "2093959907870511105",
    "h3_av_drive_flf": "2095531397845889025",
    "lipsync_windowed": "2086650291638005762",
    "lipsync_basic16": "2076998668398784513",
}

out = {}
for name, wa in APPS.items():
    try:
        d = rh.webapp_simple(wa)
        out[name] = d
        print(f"== {name} ({wa})")
        print(json.dumps(d, ensure_ascii=False)[:1200])
        print()
    except Exception as e:
        print(f"== {name} FAIL {e}")

dest = Path(r"D:\qjcNetDiskDownload\deepseek-harness\project\821\output\research_voice\webapp_nodeinfo_raw.json")
dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("saved ->", dest)
