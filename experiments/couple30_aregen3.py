# -*- coding: utf-8 -*-
"""couple30 A-segment route-乙 v3: prompt-controlled audio-driven i2v.

FLF webapp (v1/v2) failed: no prompt to pin the scene -> mid-video tea-table
drift. This route (webapp 2095429364939161601) has a full prompt field
(node 138) using the official H3 structure: subject_definitions (identity AND
environment anchor with explicit no-drift/no-scene-change clauses), summary,
retention_analysis, detailed_description with <d>[中文] line</d> tags,
overall_soundscape, non_diegetic_music.

Usage: python -X utf8 experiments/couple30_aregen3.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "820"))
sys.path.insert(0, str(ROOT / "experiments"))

from experiments import rh_task  # noqa: E402
import couple30_repair as rep  # noqa: E402

KF = ROOT / "examples" / "couple30_v1" / "keyframes"
AUD = ROOT / "output" / "creative_v2" / "couple30_v1" / "audio"
OUT = rep.OUT
APP = "2095429364939161601"
STATE = OUT / "aregen3_state.json"

PROMPT = """subject_definitions:
<Subject 1> is the young woman lying prone on top of the man in <Image 1>, with VERY LONG dark-brown hair reaching mid-back — her hair stays clearly LONGER than shoulder length in EVERY frame, never shoulder-length, never cut — wearing the ivory pajamas with blue trim exactly as in <Image 1>; her face, hairstyle, build and outfit must STRICTLY match <Image 1> in every frame.
<Subject 2> is the young man lying in bed in <Image 1>, short black hair, light-grey pajamas, exactly as in <Image 1> in every frame.
<Image 1> is the identity and environment anchor and must be STRICTLY followed: the same bright morning bedroom, sheer curtains with warm sunlight, white bedding, and the same two-person pose (woman prone over the man on the bed) must remain exactly as <Image 1> in every frame of the whole clip. Do NOT redesign, restyle, or drift from <Image 1>. No scene change, no new rooms, no tables, no tea sets, no cutting away from the bed; the camera stays on the bed the entire time.
<Audio 1> is the actual dialogue soundtrack: <Subject 1> and <Subject 2> speak their Chinese lines using the exact voices from <Audio 1>, lip movements matched to the audio.

summary:
[Reference-based generation] In the morning bedroom of <Image 1>, <Subject 1> (the woman) tries to wake <Subject 2> (the man) for brunch; he keeps bargaining for five more minutes; she pinches his nose until he gives in, laughing. Single continuous 15-second shot, fixed camera framing both faces on the bed. Both characters and the bedroom STRICTLY follow <Image 1> at all times. Voices are the real voices from <Audio 1>.

retention_analysis:
<Subject 1> (appears in [Shot 1]): fully_preserved - identity STRICTLY locked to <Image 1>: face, VERY LONG mid-back dark-brown hair (never shoulder-length in any frame), build, ivory-blue pajamas; she stays prone over the man on the bed the whole time.
<Subject 2> (appears in [Shot 1]): fully_preserved - identity STRICTLY locked to <Image 1>; he stays lying in the same bed position.
<Image 1> (character & scene reference): fully_preserved - the bedroom, curtains, morning light, white bedding and the two-person pose are copied exactly; no scene change, no drift, no cutaway, no additional objects.
<Audio 1> (actual dialogue): fully_preserved / audio_transfer - both characters speak the specified Chinese lines with the voices from <Audio 1>, lips matched.

detailed_description:
0-3s: <Subject 1> pats <Subject 2>'s cheek and says <d>[中文] 醒醒，太阳晒屁股了。</d>; he squints, pulls the quilt, mumbles <d>[中文] ……没晒到，拉了窗帘。</d>
3-8s: she props her chin, coaxes <d>[中文] 起来嘛，说好的那家 brunch，去晚了排队。</d> while tugging the quilt; he frowns and answers <d>[中文] 再睡五分钟。</d>
8-12s: she raises her eyebrows, taps his shoulder: <d>[中文] 你五分钟之前也是这么说的。</d>
12-15s: he opens one eye, gives up with a laugh: <d>[中文] 行行行，起——</d>; she beams and playfully pinches his nose; both laughing, ending pose close to the woman pinching the man's nose on the bed.

overall_soundscape: soft bedding rustle, quiet warm morning room tone, faint distant birds outside the window; no other sounds.
non_diegetic_music: none."""


def main() -> int:
    st = json.loads(STATE.read_text(encoding="utf-8-sig")) if STATE.exists() else {}
    key = rh_task.load_api_key()
    node_info = [
        {"nodeId": "139", "fieldName": "image",
         "fieldValue": rh_task.upload_file(key, KF / "KF_A1_corrected.png")},
        {"nodeId": "152", "fieldName": "audio",
         "fieldValue": rh_task.upload_file(key, AUD / "segA_dialogue.wav")},
        {"nodeId": "138", "fieldName": "value", "fieldValue": PROMPT},
    ]
    tid = rh_task.run_webapp(key, APP, node_info)
    print(f"task {tid}", flush=True)
    st["task"] = tid
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    result = None
    deadline = time.time() + 3000
    while time.time() < deadline:
        try:
            result = rh_task.task_outputs(key, tid)
            break
        except Exception as e:
            msg = f"{type(e).__name__}: {str(e)[:80]}"
            if "STATUS_ERROR" in msg:
                raise SystemExit(f"task failed server-side: {msg}")
            print(f"poll: {msg}", flush=True)
            time.sleep(30)
    if result is None:
        raise SystemExit("timeout")
    urls = rh_task.collect_file_urls(result)
    if not urls:
        raise SystemExit("no outputs")
    dest = OUT / "A_regen3_00.mp4"
    rh_task.download(urls[0], dest)
    m = rep.measure(dest)
    st.update({"output": str(dest), "measure": m})
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    print("A_regen3 measure:", json.dumps(m, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
