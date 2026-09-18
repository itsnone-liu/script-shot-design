# -*- coding: utf-8 -*-
"""couple30 v2.1: regenerate B and C via the proven audio-driven i2v+prompt
route (webapp 2095429364939161601) so dialogue lipsync is baked in by
construction — same recipe that made A_regen3 the only lipsync-correct arm.

B: 7s  man pulls woman back into bed, playful tumble  (L07/L08)
C: 13s man pins woman, teasing banter, settle to cuddle (L09/L10/L11)

Usage: python -X utf8 experiments/couple30_bcregen.py [--only B|C]
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

PROMPT_B = """subject_definitions:
<Subject 1> is the young man in <Image 1>, short black hair, light-grey pajamas, exactly as in <Image 1> in every frame.
<Subject 2> is the young woman in <Image 1>, with VERY LONG dark-brown hair reaching mid-back — her hair stays clearly LONGER than shoulder length in EVERY frame, never shoulder-length — wearing ivory pajamas with blue trim exactly as in <Image 1>.
<Image 1> is the identity and environment anchor and must be STRICTLY followed: the same bright morning bedroom, sheer curtains, warm sunlight, white bedding; the two people start in the exact pose of <Image 1>. Do NOT redesign, restyle, or drift; no scene change, no new objects, no cutting away from the bed; camera stays on the bed.
<Audio 1> is the actual soundtrack: <Subject 1> speaks his one Chinese line at the very start using the voice from <Audio 1>; after that NOBODY speaks — the woman only LAUGHS with her real laughter from <Audio 1>; all lip movements match the audio exactly.

summary:
[Reference-based generation] In the morning bedroom of <Image 1>, <Subject 2> tries to slip out of bed; <Subject 1> grabs her waist and says his line with a lazy grin; then a WORDLESS playful struggle — he pulls her back, they tumble under the duvet, she LAUGHS (no speech), ending tangled together, her face nuzzled into his shoulder still laughing. Single continuous 8-second shot, fixed camera. Both characters and the bedroom STRICTLY follow <Image 1>.

retention_analysis:
<Subject 1>: fully_preserved - identity STRICTLY locked to <Image 1>; light-grey pajamas; he stays on the bed.
<Subject 2>: fully_preserved - identity STRICTLY locked to <Image 1>; VERY LONG mid-back dark-brown hair in every frame; ivory-blue pajamas; she stays on the bed laughing (never speaking after the first two seconds).
<Image 1>: fully_preserved - bedroom, curtains, morning light, white bedding copied exactly; no scene change, no drift, no cutaway.
<Audio 1>: fully_preserved / audio_transfer - the man speaks the specified Chinese line at the start with the voice from <Audio 1>; afterwards only the woman's laughter from <Audio 1> is heard and her mouth/expressions match laughing, never talking.

detailed_description:
0-2s: <Subject 2> lifts the duvet to slip out; <Subject 1> wraps an arm around her waist, pulls her back and says <d>[中文] 再睡五分钟——这回你陪我。</d> with a lazy grin.
2-8s: right after his line he moves FAST — in one swift playful move he flips her over onto her back; she bursts into NON-STOP laughter that continues through the whole tussle (mouth open in laughter, never speaking), squirming and pushing his shoulder between laughs; they end tangled together, her face nuzzled into his shoulder, laughter fading to soft giggles; warm morning light.

overall_soundscape: duvet and bedding rustling, playful movement, the woman's laughter; no other sounds, no speech after the man's opening line.
non_diegetic_music: none."""

PROMPT_C = """subject_definitions:
<Subject 1> is the young man in <Image 1>, short black hair, light-grey pajamas, exactly as in <Image 1> in every frame.
<Subject 2> is the young woman in <Image 1>, with VERY LONG dark-brown hair reaching mid-back — her hair stays clearly LONGER than shoulder length in EVERY frame, never shoulder-length — wearing ivory pajamas with blue trim exactly as in <Image 1>.
<Image 1> is the identity and environment anchor and must be STRICTLY followed: the same bright morning bedroom, sheer curtains, warm sunlight, white bedding; the two people start in the exact pose of <Image 1> (the man over the woman on the bed). Do NOT redesign, restyle, or drift; no scene change, no new objects, no cutting away from the bed; camera stays on the bed.
<Audio 1> is the actual dialogue soundtrack: <Subject 1> and <Subject 2> speak their Chinese lines using the exact voices from <Audio 1>, lip movements matched.

summary:
[Reference-based generation] In the morning bedroom of <Image 1>, <Subject 1> has just pinned <Subject 2> on the bed; she calls out his faking, he confesses his brunch trap with a smug smile; she asks the time, he shrugs; they settle into a lazy cuddle in silence. Single continuous 13-second shot, fixed camera. Both characters and the bedroom STRICTLY follow <Image 1>. Voices are the real voices from <Audio 1>.

retention_analysis:
<Subject 1>: fully_preserved - identity STRICTLY locked to <Image 1>; light-grey pajamas; he stays leaning over her on the bed.
<Subject 2>: fully_preserved - identity STRICTLY locked to <Image 1>; VERY LONG mid-back dark-brown hair in every frame; ivory-blue pajamas; she stays lying on the bed beneath him.
<Image 1>: fully_preserved - bedroom, curtains, morning light, white bedding copied exactly; no scene change, no drift, no cutaway.
<Audio 1>: fully_preserved / audio_transfer - both speak the specified Chinese lines with the voices from <Audio 1>, lips matched.

detailed_description:
0-1.5s: as he pins her hands lightly above the pillow, she gives him a look and protests <d>[中文] 你根本就是装的！</d>
1.9-5.5s: he looks down with a smug smile and confesses <d>[中文] 从你提 brunch 那句开始，我就在想怎么把你按回来。</d>
5.7-7.4s: she squirms once, glances aside, asks <d>[中文] 那……现在几点了？</d>
7.6-11s: he shrugs, lowers himself closer, answers lazily <d>[中文] 不知道。反正——再五分钟。</d>
11-13s: wordless — she gives up with a soft smile; he nestles into her shoulder; both close their eyes halfway, her long hair spread on the pillow, warm morning light.

overall_soundscape: soft bedding rustle, quiet warm morning room tone, faint distant birds; no other sounds.
non_diegetic_music: none."""

SEGS = {
    "B": {"kf": "KF_B1.png",
          "aud": "segB_perf5.wav" if (AUD / "segB_perf5.wav").exists()
          else "segB_perf3.wav" if (AUD / "segB_perf3.wav").exists()
          else "segB_perf2.wav" if (AUD / "segB_perf2.wav").exists()
          else "segB_dialogue.wav",
          "prompt": PROMPT_B,
          "out": ("B_regen4_00.mp4" if (AUD / "segB_perf5.wav").exists()
                  else "B_regen3_00.mp4" if (AUD / "segB_perf3.wav").exists()
                  else "B_regen2_00.mp4" if (AUD / "segB_perf2.wav").exists()
                  else "B_regen_00.mp4")},
    "C": {"kf": "KF_C1.png",
          "aud": "segC_perf.wav" if (AUD / "segC_perf.wav").exists()
          else "segC_dialogue.wav",
          "prompt": PROMPT_C,
          "out": ("C_regen2_00.mp4" if (AUD / "segC_perf.wav").exists()
                  else "C_regen_00.mp4")},
}
STATE = OUT / "bcregen_state.json"


def run_seg(key: str, api_key: str) -> None:
    cfg = SEGS[key]
    node_info = [
        {"nodeId": "139", "fieldName": "image",
         "fieldValue": rh_task.upload_file(api_key, KF / cfg["kf"])},
        {"nodeId": "152", "fieldName": "audio",
         "fieldValue": rh_task.upload_file(api_key, AUD / cfg["aud"])},
        {"nodeId": "138", "fieldName": "value", "fieldValue": cfg["prompt"]},
    ]
    tid = rh_task.run_webapp(api_key, APP, node_info)
    print(f"[{key}] task {tid}", flush=True)
    result = None
    deadline = time.time() + 3000
    while time.time() < deadline:
        try:
            result = rh_task.task_outputs(api_key, tid)
            break
        except Exception as e:
            msg = f"{type(e).__name__}: {str(e)[:80]}"
            if "STATUS_ERROR" in msg:
                raise SystemExit(f"[{key}] task failed server-side: {msg}")
            print(f"[{key}] poll: {msg}", flush=True)
            time.sleep(30)
    if result is None:
        raise SystemExit(f"[{key}] timeout")
    urls = rh_task.collect_file_urls(result)
    if not urls:
        raise SystemExit(f"[{key}] no outputs")
    dest = OUT / cfg["out"]
    # outputs list = [zip, mp4] in arbitrary order — pick the .mp4
    mp4 = next((u for u in urls if str(u).rstrip("/").lower().endswith(".mp4")),
               None)
    if not mp4:
        raise SystemExit(f"[{key}] no mp4 in outputs: {urls}")
    rh_task.download(mp4, dest)
    m = rep.measure(dest)
    print(f"[{key}] measure:", json.dumps(m, ensure_ascii=False), flush=True)
    st = json.loads(STATE.read_text(encoding="utf-8-sig")) if STATE.exists() else {}
    st[key] = {"task": tid, "output": str(dest), "measure": m}
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> int:
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]
    key = rh_task.load_api_key()
    for seg in SEGS:
        if only and seg != only:
            continue
        run_seg(seg, key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
