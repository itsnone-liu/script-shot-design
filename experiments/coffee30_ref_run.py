# -*- coding: utf-8 -*-
"""coffee30_ref_run.py — 821 咖啡故事版参考图生成(复用 820 Z-Image-Turbo 骨架链)
用法: python coffee30_ref_run.py <skeleton.png> <out_name> <seed> <mode>
mode: portrait | window | still
生成后写入 _coffee30_ref_manifest.json
"""
import io, json, sys, time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
ROOT = Path(__file__).resolve().parents[1]
R820 = ROOT.parent / "820"
sys.path.insert(0, str(R820)); sys.path.insert(0, str(R820 / "experiments"))
from experiments import rh_task  # noqa: E402

CID = "2094584429485608961"
REF = ROOT / "output/script_first/coffee30_story_v1/ref"

PORTRAIT_POS = (
    "Cinematic photorealistic portrait, a young Chinese woman around twenty-eight years old, "
    "gently beautiful calm face, eyes softly closed as if just waking, natural East Asian Chinese "
    "facial features, smooth real skin with visible pores and subtle morning flush, dark "
    "shoulder-length hair resting on a white pillow, wearing a cream cotton sleep top, soft white "
    "bedding, first morning sunlight from a window grazing the edge of her hair, shallow depth of "
    "field, 35mm live-action commercial cinematography, filmic soft contrast, tranquil domestic "
    "morning mood, photorealistic."
)
PORTRAIT_NEG = (
    "anime, manga, illustration, CGI render, plastic skin, wax figure, doll face, stylized "
    "proportions, heavy makeup, jewelry, earrings, glasses, watermark, text, logo, extra person, "
    "second face, hands near face, wide open eyes, smiling, cartoon, 3d render, painting"
)
WINDOW_POS = (
    "Cinematic photorealistic photo, the same young Chinese woman around twenty-eight sitting up "
    "in a soft white bed by a bright window, holding a white ceramic coffee cup with both hands "
    "near her chest, steam curling up through the morning sunbeam, she gazes toward the window "
    "with a gentle happy smile, natural East Asian Chinese facial features, real skin with "
    "visible pores, dark shoulder-length hair slightly mussed from sleep, cream cotton sleep top, "
    "soft warm morning light from the left, city softly out of focus outside, 35mm live-action "
    "commercial cinematography, filmic soft contrast, tranquil beautiful morning mood, photorealistic."
)
STILL_POS = (
    "Photorealistic commercial still life, a glass jar of dark roasted coffee beans and two white "
    "ceramic cups on a light wooden bedside table, first morning sunlight through sheer curtains "
    "entering from the left, soft long shadows, a thin wisp of steam, shallow depth of field, "
    "35mm live-action commercial cinematography, filmic soft contrast, tranquil morning mood, "
    "photorealistic."
)
STILL_NEG = (
    "people, person, human, hands, face, anime, illustration, CGI render, plastic look, text, "
    "watermark, logo, cartoon, painting"
)

MODES = {
    "portrait": (PORTRAIT_POS, PORTRAIT_NEG),
    "window": (WINDOW_POS, PORTRAIT_NEG),
    "still": (STILL_POS, STILL_NEG),
}


def main() -> int:
    skel, name, seed, mode = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    pos, neg = MODES[mode]
    key = rh_task.load_api_key()
    u = rh_task.upload_file(key, skel)
    print("[upload]", u)
    fmt = json.loads((R820 / "_zpose_apifmt.json").read_text(encoding="utf-8"))
    fmt["30"]["inputs"]["image"] = u
    fmt["6"]["inputs"]["text"] = pos
    fmt["7"]["inputs"]["text"] = neg
    fmt["28"]["inputs"]["image"] = ["30", 0]
    fmt["28"]["inputs"]["strength"] = 1
    fmt["3"]["inputs"]["seed"] = seed
    fmt["3"]["inputs"]["steps"] = 15
    fmt["40"]["inputs"]["scale_to_length"] = 1920
    fmt.pop("39", None)
    fmt.pop("33", None)
    tid = rh_task.run_workflow_json(key, json.dumps(fmt, ensure_ascii=False), sandbox_id=CID)
    print("[task]", tid)
    while True:
        s = rh_task.task_status(key, tid)
        print("[status]", s, flush=True)
        if s not in ("RUNNING", "QUEUED", "PENDING", "QUEUE"):
            break
        time.sleep(15)
    outs = rh_task.task_outputs(key, tid)
    urls = rh_task.collect_file_urls(outs)
    print("[urls]", urls)
    out_path = REF / f"{name}.png"
    ok = False
    for u2 in urls:
        if u2.lower().split("?")[0].endswith((".png", ".jpg", ".jpeg", ".webp")):
            rh_task.download(u2, str(out_path))
            print("[saved]", out_path)
            ok = True
            break
    mf = REF / "_coffee30_ref_manifest.json"
    m = json.loads(mf.read_text(encoding="utf-8")) if mf.exists() else []
    m.append({"name": name, "seed": seed, "mode": mode, "skeleton": skel, "task": tid,
              "status": "success" if ok else "failed"})
    mf.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
