# -*- coding: utf-8 -*-
"""Generate concert30 keyframes with the Flux Kontext character-consistency workflow.

Usage:
  python experiments/run_concert30_hcy_flowers.py --dry          # print prompts only, no paid calls
  python experiments/run_concert30_hcy_flowers.py KF_A_FIRST     # one keyframe (paid)
  python experiments/run_concert30_hcy_flowers.py all            # all remaining (paid)

Hard gate: both segA/segB contracts must carry user_script_review.status=approved.
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
ROOT = Path(__file__).resolve().parents[1]
R820 = ROOT.parent / "820"
sys.path.insert(0, str(R820))
sys.path.insert(0, str(R820 / "experiments"))
from experiments import rh_task  # noqa: E402

CID = "1940886562836213761"  # Flux Kontext consistent characters
SRC = ROOT / "examples" / "concert30_hcy_flowers"
OUT = ROOT / "output" / "concert30_hcy_flowers_v1" / "ref"
OUT.mkdir(parents=True, exist_ok=True)
SEED = 20260914

HER = (
    "Capture the same young Chinese woman from the reference photo — soft oval face, fair skin, "
    "thin round metal-framed glasses always worn, dark brown mid-parted hair past her shoulders, "
    "matte red-brown lips, plain unbranded loose bright-red long-sleeve top with no logo or print, "
    "fine thin necklace. "
)
HIM = (
    "Beside her stands the same Chinese male pop singer around thirty — slim build, silver-gray "
    "highlighted short hair, black stage shirt, holding a red microphone. "
)
STYLE = (
    "Live-action 35mm concert cinematography, true photorealism, natural film grain, real skin "
    "pores and fabric weave, physically plausible contact, shallow depth of field. "
)
ANTI = (
    "No readable text, no logo, no watermark, no UI, no anime or illustration look, no plastic "
    "skin, no wax face, no extra fingers, no clear faces in the crowd, no third person."
)

SPECS = {
    "KF_A_FIRST": {
        "seed": SEED + 11,
        "positive": (
            HER
            + "Night open-air stadium concert stands: she sits hugging a kraft-paper-wrapped "
            "bouquet of red roses against her chest at the left third of frame, fingers tightening "
            "on the paper, watching the distant stage. Around her an ocean of red glow sticks held "
            "by a deeply blurred crowd; giant stage far frame right as soft bokeh; her face half "
            "lit by the distant warm stage wash, red ambient under-glow. " + STYLE + ANTI
        ),
    },
    "KF_A_LAST": {
        "seed": SEED + 12,
        "positive": (
            HER
            + HIM
            + "Low angle from the base of the stage stairs looking up: she stands at the stair "
            "bottom at frame left hugging the red-rose bouquet, chin tilted up toward the stage; "
            "above right on the stage the silver-haired singer has turned to look down at her, "
            "semi-silhouetted with strong top-back rim light, red microphone in hand. The red "
            "bouquet and the red microphone share one frame for the first time. Stage-edge line "
            "divides the diagonal, volume haze in the beams, red sea bokeh beyond. " + STYLE + ANTI
        ),
    },
    "KF_B_FIRST": {
        "seed": SEED + 13,
        "positive": (
            HER
            + HIM
            + "On the concert main stage, frontal medium two-shot: she stands frame left extending "
            "the kraft-wrapped red-rose bouquet toward him with both hands, elbows soft, a small "
            "head bow; he is half a head taller at frame right, receiving her gaze, red microphone "
            "in his right hand. Front follow-spot key on the pair, cool giant LED screen backlight "
            "halo behind them as soft bokeh, red glow sea beyond the stage, volume haze. " + STYLE + ANTI
        ),
    },
    "KF_B_LAST": {
        "seed": SEED + 14,
        "positive": (
            HER
            + HIM
            + "A real photograph frozen mid-flash at a concert: warm print tone, visible photo "
            "grain, both facing the camera shoulder to shoulder — she makes a clearly readable "
            "single-hand heart beside her shoulder by touching thumb and index finger into a heart "
            "shape, the other three fingers naturally curled, never a V sign; he holds the red-rose "
            "bouquet over his shoulder with one hand and a clearly bright-red microphone body, "
            "including its grille, in the other, smiling. Camera flashes bloom as soft white circles "
            "over the blurred red glow sea behind them. " + STYLE + ANTI
        ),
    },
}

REF_MAIN = SRC / "refs" / "ref06_concert_poster_red_tee.jpg"


def check_approval() -> None:
    for name in ("segA_v1.json", "segB_v1.json"):
        doc = json.loads((SRC / name).read_text(encoding="utf-8"))
        rv = doc.get("user_script_review", {})
        if rv.get("status") != "approved" or rv.get("script_version") != "concert30-hcy-flowers-v1":
            raise SystemExit(f"approval gate: {name} is not approved — refusing paid render")


def crop_169(source: Path, target: Path) -> None:
    result = subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", str(source),
        "-vf", "crop='min(iw,ih*16/9)':'min(ih,iw*9/16)',scale=1600:900:flags=lanczos",
        "-frames:v", "1", str(target),
    ])
    if result.returncode:
        raise RuntimeError(f"ffmpeg crop failed for {source}")


def generate(name: str, ref_uploaded: str) -> dict:
    spec = SPECS[name]
    key = rh_task.load_api_key()
    fmt = json.loads((SRC / "kontext_apifmt.json").read_text(encoding="utf-8"))
    fmt["6"]["inputs"]["text"] = spec["positive"]
    fmt["25"]["inputs"]["noise_seed"] = spec["seed"]
    fmt["41"]["inputs"]["image"] = ref_uploaded
    task_id = rh_task.run_workflow_json(key, json.dumps(fmt, ensure_ascii=False), sandbox_id=CID)
    print(name, "task", task_id, flush=True)
    while True:
        state = rh_task.task_status(key, task_id)
        print(name, state, flush=True)
        if state not in ("RUNNING", "QUEUED", "PENDING", "QUEUE"):
            break
        time.sleep(15)
    urls = rh_task.collect_file_urls(rh_task.task_outputs(key, task_id))
    raw = OUT / f"{name}_raw.png"
    ok = False
    for url in urls:
        if url.lower().split("?")[0].endswith((".png", ".jpg", ".jpeg", ".webp")):
            rh_task.download(url, str(raw))
            ok = True
            break
    if not ok:
        return {"id": name, "task_id": task_id, "status": "failed", "urls": urls}
    final = OUT / f"{name}.png"
    crop_169(raw, final)
    return {"id": name, "task_id": task_id, "status": "success", "raw": str(raw), "final": str(final), "seed": spec["seed"]}


def main() -> int:
    args = sys.argv[1:]
    dry = "--dry" in args
    force = "--force" in args
    args = [a for a in args if a not in ("--dry", "--force")]
    requested = args[0] if args else "all"
    names = list(SPECS) if requested == "all" else [requested]
    for n in names:
        if n not in SPECS:
            print("unknown keyframe", n)
            return 2
    check_approval()
    manifest_path = OUT / "keyframe_manifest.json"
    prior = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
    by = {x["id"]: x for x in prior}
    if dry:
        for n in names:
            print(f"---- {n} (seed {SPECS[n]['seed']}) ----")
            print(SPECS[n]["positive"])
            print()
        print("dry run only: no tasks submitted")
        return 0
    key = rh_task.load_api_key()
    ref_uploaded = rh_task.upload_file(key, str(REF_MAIN))
    print("ref uploaded:", ref_uploaded, flush=True)
    for n in names:
        if not force and by.get(n, {}).get("status") == "success" and Path(by[n]["final"]).exists():
            print(n, "already successful")
            continue
        result = generate(n, ref_uploaded)
        by[n] = result
        manifest_path.write_text(json.dumps(list(by.values()), ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if result["status"] != "success":
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
