# -*- coding: utf-8 -*-
"""Generate C1 v1 cinematic keyframes with the established Z-Image pose workflow.

Usage:
  python experiments/coffee30_dont_wake_her_refs.py KF_A_FIRST
  python experiments/coffee30_dont_wake_her_refs.py all

Outputs raw images plus 16:9 crops under output/creative_v2/.../ref.
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
ROOT = Path(__file__).resolve().parents[1]
R820 = ROOT.parent / "820"
sys.path.insert(0, str(R820))
sys.path.insert(0, str(R820 / "experiments"))
from experiments import rh_task  # noqa: E402

CID = "2094584429485608961"
OUT = ROOT / "output" / "creative_v2" / "coffee30_dont_wake_her_v1" / "ref"
OUT.mkdir(parents=True, exist_ok=True)
SEED = 20260916
W, H = 1600, 1200

COMMON_POS = (
    "live-action 35mm commercial cinematography, true photorealism, natural film grain, "
    "real materials and physically plausible contact, one hard sunrise source from upper left, "
    "cool ambient window fill, all shadows lower right, shallow depth of field, restrained intimate suspense, "
    "modern Chinese bedroom, soft white bedding and light wooden bedside table, no branding"
)
COMMON_NEG = (
    "anime, manga, illustration, painting, CGI render, plastic skin, wax figure, doll, stylized proportions, "
    "heavy makeup, extra person, duplicate face, duplicate cup, extra fingers, fused fingers, malformed hands, "
    "floating object, impossible contact, readable text, logo, watermark, UI, blue title, fragrance visualization"
)
WOMAN = (
    "the same young Chinese woman around twenty-eight, soft oval face, natural East Asian features, "
    "dark shoulder-length hair, cream cotton sleep top, real skin pores, natural eyebrows and lips"
)

SPECS = {
    "KF_A_FIRST": {
        "seed": SEED + 101,
        "pose": "sleep_bg",
        "positive": (
            "cinematic macro at wooden bedside-table height, one realistic dark roasted coffee bean just beginning "
            "to roll left-to-right toward the sharp table edge, a realistic male index fingertip entering from left but "
            "not touching yet; in the upper-right distant background, " + WOMAN + " lies asleep with eyes closed on a white pillow, heavily soft-focus; "
            "bean and table edge are dominant and sharp, woman is only risk context, " + COMMON_POS
        ),
        "negative": COMMON_NEG + ", open eyes, smile, multiple beans, hand covering bean, foreground face",
    },
    "KF_A_LAST": {
        "seed": SEED + 102,
        "pose": "blank",
        "positive": (
            "cinematic extreme macro of freshly brewed dark coffee inside one unlabeled white ceramic cup beneath a pour-over brewer, "
            "the real liquid surface has just settled mirror-still with subtle crema micro-bubbles, one thin natural steam ribbon crosses the sunrise, "
            "no hand and no person visible, coffee product and physical liquid texture dominate, " + COMMON_POS
        ),
        "negative": COMMON_NEG + ", person, hand, face, latte art, heart shape, large splash, whole beans in liquid, multiple cups",
    },
    "KF_B_FIRST": {
        "seed": SEED,
        "pose": "sleep_close",
        "positive": (
            "pillow-height cinematic profile close-up of " + WOMAN + " apparently asleep on frame right, eyes softly closed, no smile, "
            "the blurred rim of one white hot coffee cup is visibly present at the lower-left foreground and one thin natural steam ribbon rises directly from that rim; "
            "at the lower-center blanket edge exactly one anatomically correct fingertip visibly peeks from beneath a cotton fold, small but readable; "
            "face and eyelashes are the focus, fingertip is a quiet secondary clue, " + COMMON_POS
        ),
        "negative": COMMON_NEG + ", open eyes, grin, cup covering face, hand near face, more than one visible finger, perfume smoke",
    },
    "KF_B_LAST": {
        "seed": SEED + 103,
        "pose": "blank",
        "positive": (
            "clean cinematic product-only hero composition, exactly one unlabeled white ceramic cup filled with dark coffee alone and centered on the lower third in hard sunrise, "
            "the full cup silhouette is completely unobstructed, one irregular natural steam ribbon rises from the coffee, ample clean negative space, "
            "no person, no face, no hand and no human body anywhere in this final image; coffee is the only visual subject, " + COMMON_POS
        ),
        "negative": COMMON_NEG + ", person, woman, man, face, portrait, hand, finger, arm, holding cup, drinking, two cups, empty cup",
    },
}

LIMBS = [(1,2),(1,5),(2,3),(3,4),(5,6),(6,7),(1,8),(8,9),(9,10),(1,11),(11,12),(12,13),(1,0),(0,14),(0,15),(14,16),(15,17)]


def draw_pose(kind: str, path: Path) -> None:
    image = Image.new("RGB", (W, H), (0, 0, 0))
    if kind == "blank":
        image.save(path)
        return
    draw = ImageDraw.Draw(image)
    if kind in ("sleep_bg", "sleep_close"):
        if kind == "sleep_bg":
            pts = {0:(1260,410),1:(1190,470),2:(1120,485),5:(1260,500),3:(1040,540),6:(1330,555),4:(980,590),7:(1390,610),8:(1140,620),11:(1240,640),14:(1240,390),15:(1280,400)}
        else:
            pts = {0:(1050,340),1:(930,500),2:(790,520),5:(1040,560),3:(650,610),6:(1130,690),4:(520,720),7:(1240,790),8:(860,800),11:(1010,820),14:(1010,315),15:(1080,335)}
    else:  # hero_bg
        pts = {0:(1120,310),1:(1080,440),2:(960,470),5:(1190,475),3:(900,620),6:(1260,630),4:(840,760),7:(1320,770),8:(1010,760),11:(1150,770),14:(1085,285),15:(1150,295)}
    colors=[(255,0,0),(255,85,0),(255,170,0),(255,255,0),(170,255,0),(85,255,0),(0,255,0),(0,255,85),(0,255,170),(0,255,255),(0,170,255),(0,85,255),(0,0,255),(85,0,255),(170,0,255),(255,0,255),(255,0,170)]
    for (a,b),color in zip(LIMBS,colors):
        if a in pts and b in pts:
            draw.line([pts[a],pts[b]],fill=color,width=12)
    for key,(x,y) in pts.items():
        r=11 if key<14 else 9
        draw.ellipse((x-r,y-r,x+r,y+r),fill=(255,64,64))
    image.save(path)


def crop_169(source: Path, target: Path) -> None:
    result = subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", str(source),
        "-vf", "crop='min(iw,ih*16/9)':'min(ih,iw*9/16)',scale=1600:900:flags=lanczos",
        "-frames:v", "1", str(target),
    ])
    if result.returncode:
        raise RuntimeError(f"ffmpeg crop failed for {source}")


def generate(name: str) -> dict:
    spec = SPECS[name]
    pose = OUT / f"{name}_pose.png"
    draw_pose(spec["pose"], pose)
    key = rh_task.load_api_key()
    uploaded = rh_task.upload_file(key, str(pose))
    fmt = json.loads((R820 / "_zpose_apifmt.json").read_text(encoding="utf-8"))
    fmt["30"]["inputs"]["image"] = uploaded
    fmt["6"]["inputs"]["text"] = spec["positive"]
    fmt["7"]["inputs"]["text"] = spec["negative"]
    fmt["28"]["inputs"]["image"] = ["30", 0]
    fmt["28"]["inputs"]["strength"] = 1
    fmt["3"]["inputs"]["seed"] = spec["seed"]
    fmt["3"]["inputs"]["steps"] = 15
    fmt["40"]["inputs"]["scale_to_length"] = 1920
    fmt.pop("39", None)
    fmt.pop("33", None)
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
        return {"id":name,"task_id":task_id,"status":"failed","urls":urls}
    final = OUT / f"{name}.png"
    crop_169(raw, final)
    return {"id":name,"task_id":task_id,"status":"success","raw":str(raw),"final":str(final),"seed":spec["seed"]}


def main() -> int:
    requested = sys.argv[1] if len(sys.argv)>1 else "all"
    names = list(SPECS) if requested == "all" else [requested]
    manifest_path = OUT / "keyframe_manifest.json"
    prior = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
    by = {x["id"]:x for x in prior}
    for name in names:
        if name not in SPECS:
            print("unknown keyframe", name)
            return 2
        if by.get(name,{}).get("status") == "success" and Path(by[name]["final"]).exists():
            print(name,"already successful")
            continue
        result = generate(name)
        by[name]=result
        manifest_path.write_text(json.dumps(list(by.values()),ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps(result,ensure_ascii=False),flush=True)
        if result["status"] != "success":
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
