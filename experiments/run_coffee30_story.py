"""coffee30 story v1: light wakes the room, coffee wakes her.
SegA pure t2v (sleeping face is mid-segment, one calm static shot).
SegB t2v_variable + first/last-frame keyframe conditioning (bedside cup /
her smile with cup at window) - the reference-image workflow experiment.
Stitch A+B into coffee30_story_v1_master.mp4.
"""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from shortfilm.prompt_contract import compile_minimax_prompt, validate_director_contract
from shortfilm.rh_adapter import render_packet

REF = ROOT / "output/script_first/coffee30_story_v1/ref"
OUT = ROOT / "output/script_first/coffee30_story_v1"
KF_B1 = REF / "kf_b1_169.png"   # first frame  (16:9 crop)
KF_B2 = REF / "kf_b2_169.png"   # last frame   (16:9 crop)

# i2v card verified overrides: 142 first-frame megapixels 0.4->0.6 (match
# t2v_variable 15s tier); 175 baked-in research style LoRA -> strength 0.
I2V_OVERRIDES = [
    {"nodeId": "142", "fieldName": "value", "fieldValue": "0.6"},
    {"nodeId": "175", "fieldName": "strength_model", "fieldValue": "0"},
]

SEGS = [
    ("COFFEE30S_A", "examples/script_first/coffee30_story_segA_v1.json", "", "", None),
    ("COFFEE30S_B", "examples/script_first/coffee30_story_segB_v1.json", KF_B1, KF_B2, "i2v"),
]


def main() -> int:
    manifest = OUT / "asset_manifest.json"
    by = {}
    if manifest.exists():
        by = {x["shot_id"]: x for x in json.loads(manifest.read_text(encoding="utf-8")).get("results", [])}
    for sid, contract_rel, ref, last_ref, wf in SEGS:
        if by.get(sid, {}).get("status") == "success":
            continue
        doc = json.loads((ROOT / contract_rel).read_text(encoding="utf-8"))
        r = doc.get("user_script_review") or {}
        if r.get("status") != "approved" or not r.get("reviewed_by"):
            print("REFUSED - direct user approval required", sid)
            return 2
        errs = validate_director_contract(doc)
        if errs:
            print("CONTRACT INVALID", sid, *errs, sep="\n- ")
            return 3
        if ref and not Path(ref).exists():
            print("missing keyframe", ref)
            return 4
        prompt = compile_minimax_prompt(doc)
        kw = dict(workflow=wf or "t2v_variable", poll=10, max_wait=2700)
        if ref:
            kw.update(reference_file=str(ref), last_reference_file=str(last_ref or ref))
        if wf == "i2v":
            kw.update(extra_nodes=I2V_OVERRIDES)
        try:
            res = render_packet({"shot_id": sid, "duration": doc["duration"], "prompt": prompt,
                                 "aspect_ratio": "16:9 (Widescreen)"}, OUT / "shots", **kw)
        except Exception as exc:
            res = {"shot_id": sid, "status": "failed", "error": str(exc)}
        by[sid] = res
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps({"contracts": [s[1] for s in SEGS],
                                        "keyframes": {"B_first": str(KF_B1), "B_last": str(KF_B2)},
                                        "results": list(by.values())}, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        print(sid, res.get("status"), res.get("task_id", ""), res.get("error", ""), flush=True)
    if not all(by.get(s, {}).get("status") == "success" for s, *_ in SEGS):
        return 1
    master = OUT / "coffee30_story_v1_master.mp4"
    if not master.exists():
        files = []
        for sid, *_ in SEGS:
            o = by[sid].get("outputs") or []
            if not o:
                print("no output for", sid)
                return 5
            files.append(o[0])
        lst = OUT / "concat.txt"
        lst.write_text("\n".join(f"file '{p}'" for p in files), encoding="utf-8")
        rc = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                             "-i", str(lst), "-c", "copy", str(master)]).returncode
        if rc != 0:
            # resolution/fps mismatch fallback: normalize both to A's spec then re-encode
            import re
            probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                                    "-show_entries", "stream=width,height,r_frame_rate",
                                    "-of", "csv=p=0", files[0]], capture_output=True, text=True).stdout.strip()
            w, h, fpsr = probe.split(",") if probe.count(",") == 2 else ("1216", "704", "24/1")
            rc = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", files[0], "-i", files[1],
                                 "-filter_complex",
                                 f"[0:v]scale={w}:{h}:flags=lanczos,setsar=1,fps={fpsr}[a];"
                                 f"[1:v]scale={w}:{h}:flags=lanczos,setsar=1,fps={fpsr}[b];"
                                 f"[a][b]concat=n=2:v=1[out]",
                                 "-map", "[out]", "-c:v", "libx264", "-crf", "18",
                                 "-pix_fmt", "yuv420p", str(master)]).returncode
        print("master_stitched" if rc == 0 else "master_failed", master, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
