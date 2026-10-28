"""Static preview assembler for coffee30 v2《未发送》(unsent).

Stitches the registry keyframes into a timed 16:9 slideshow that follows the
seg containers' internal-shot timing exactly, burns in per-shot captions
(shot_id + emotion/trigger + end_state), and lays a temporary audio track.

Purpose (phase-0 两遍法 design): verify RHYTHM and the emotional arc before
any paid video generation — if the story doesn't read as a slideshow with
correct pacing, the video won't save it.

Free end to end (local ffmpeg). Reads keyframes through the registry so the
preview can only be built from the same files the pay-gate hashed.

  python experiments/preview_coffee30_v2_unsent.py --out preview_v1.mp4 [--audio temp.mp3]
  python experiments/preview_coffee30_v2_unsent.py --placeholder   # self-test with solid frames

Exit 0 = preview written; exit 3 = missing keyframes (expected until keyframe
production runs); exit 4 = ffmpeg failure.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def ffmpeg_exe() -> str:
    """ffmpeg is not on PATH on this machine; the embedded python ships a
    static binary via imageio-ffmpeg (works for any python that has it)."""
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001 — fall back to PATH ffmpeg
        return "ffmpeg"

BASE = ROOT / "examples" / "creative_v2"
OUT_DIR = ROOT / "output" / "creative_v2" / "coffee30_v2_unsent"
REGISTRY_PATH = OUT_DIR / "keyframes_registry_v1.json"
CAPTION_DIR = OUT_DIR / "preview_captions"
FONT = Path(r"C:\Windows\Fonts\msyh.ttc")
SEGMENTS = {
    "A": BASE / "coffee30_v2_segA_v1.json",
    "B": BASE / "coffee30_v2_segB_v1.json",
    "C": BASE / "coffee30_v2_segC_v1.json",
}
W, H = 1920, 1080


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def registry_files() -> dict[str, Path]:
    registry = load_json(REGISTRY_PATH)
    base = REGISTRY_PATH.parent
    out = {}
    for kid, entry in registry["keyframes"].items():
        p = Path(entry["file"])
        out[kid] = p if p.is_absolute() else base / p
    return out


def build_plan() -> list[dict]:
    """One entry per on-screen moment: {image, seconds, caption, shot_id}."""
    files = registry_files()
    plan: list[dict] = []
    missing: list[str] = []
    for seg_name, path in SEGMENTS.items():
        doc = load_json(path)
        for shot in doc["internal_shots"]:
            kid = shot["first_frame"]["keyframe_id"]
            image = files.get(kid)
            if image is None or not image.is_file():
                missing.append(kid)
                continue
            perf = (shot.get("cinematic_design") or {}).get("performance_detail") or {}
            emotion = perf.get("emotion") or ""
            trigger = perf.get("trigger") or ""
            intent = shot.get("duration_intent") or ""
            head = f"{shot['shot_id']} [{intent}]" if intent else shot["shot_id"]
            caption = f"{head}  |  {emotion}: {trigger}" if emotion else head
            plan.append({"image": str(image), "seconds": shot["end"] - shot["start"],
                         "caption": caption, "shot_id": shot["shot_id"]})
        if seg_name == "C":  # hold is INCLUDED in the final shot, never appended
            last = files.get("KF_V2_C_LAST")
            doc_hold = float(doc.get("final_hold_seconds", 0) or 0)
            if doc_hold > 0:
                if last is None or not last.is_file():
                    missing.append("KF_V2_C_LAST")
                elif plan and plan[-1]["shot_id"] == doc["internal_shots"][-1]["shot_id"]:
                    if doc_hold > plan[-1]["seconds"]:
                        raise ValueError("final hold exceeds final shot duration")
                    plan[-1]["seconds"] -= doc_hold
                    if plan[-1]["seconds"] == 0:
                        plan.pop()
                    plan.append({"image": str(last), "seconds": doc_hold,
                                 "caption": "PRODUCT FRAME (included final hold)", "shot_id": "N10_hold"})
    if missing:
        raise FileNotFoundError("missing keyframes: " + ", ".join(missing))
    return plan


def caption_file(text: str, index: int) -> Path:
    CAPTION_DIR.mkdir(parents=True, exist_ok=True)
    path = CAPTION_DIR / f"cap_{index:02d}.txt"
    path.write_text(text, encoding="utf-8")
    return path


def _filter_path(path: Path | str) -> str:
    """ffmpeg filtergraph option values must avoid Windows drive colons (this
    build's quoting/escaping proved unreliable); the cmd runs with cwd=OUT_DIR
    and uses registry-relative paths only."""
    return Path(path).resolve().relative_to(OUT_DIR.resolve()).as_posix()


def _ensure_local_font() -> Path:
    """Copy the CJK font next to the captions once; filters reference it
    relatively. Local render asset only — never committed."""
    target = OUT_DIR / "fonts" / FONT.name
    if FONT.is_file() and not target.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(FONT.read_bytes())
    return Path("fonts") / FONT.name


def ffmpeg_cmd(plan: list[dict], out: Path, audio: Path | None) -> list[str]:
    inputs: list[str] = []
    filters: list[str] = []
    concat_inputs: list[str] = []
    for i, item in enumerate(plan):
        inputs += ["-loop", "1", "-t", f"{item['seconds']:.2f}", "-i", item["image"]]
        cap = caption_file(item["caption"], i)
        font_rel = _ensure_local_font()
        # scale + pad to 1920x1080, then burn a two-line caption near the bottom
        filters.append(
            f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"drawtext=fontfile={font_rel.as_posix()}:textfile={_filter_path(cap)}"
            f":fontcolor=white:fontsize=34:box=1:boxcolor=black@0.55:boxborderw=12:x=(w-text_w)/2:y=h-140[v{i}]"
        )
        concat_inputs.append(f"[v{i}]")
    if audio is not None:
        inputs += ["-i", str(audio)]
    graph = ";".join(filters) + ";" + "".join(concat_inputs) + f"concat=n={len(plan)}:v=1:a=0[vout]"
    cmd = ["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", graph, "-map", "[vout]"]
    if audio is not None:
        cmd += ["-map", f"{len(plan)}:a", "-shortest"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "24", str(out)]
    return [ffmpeg_exe() if part == "ffmpeg" else part for part in cmd]


def make_placeholders() -> None:
    """Self-test frames: solid colors + keyframe id, so the assembler can be
    verified before real keyframes exist. Never touches gate hashes (registry
    sha256 stays empty; gate still refuses)."""
    files = registry_files()
    palette = ["0x2b2d31", "0x54423a", "0x7a6a52", "0x9c8b6e"]
    for i, (kid, path) in enumerate(sorted(files.items())):
        path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi",
               "-i", f"color=c={palette[i % len(palette)]}:s={W}x{H}:d=1",
               "-frames:v", "1", str(path)]
        if subprocess.run(cmd).returncode:
            raise RuntimeError(f"placeholder failed for {kid}")
    print(f"placeholders written: {len(files)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUT_DIR / "preview_static_v1.mp4")
    parser.add_argument("--audio", type=Path, default=None, help="temporary audio track (optional)")
    parser.add_argument("--placeholder", action="store_true", help="write solid self-test frames into the registry slots")
    parser.add_argument("--plan-only", action="store_true", help="print the timing plan, build nothing")
    args = parser.parse_args()

    if args.placeholder:
        make_placeholders()
        return 0

    try:
        plan = build_plan()
    except FileNotFoundError as exc:
        print(f"PREVIEW BLOCKED - {exc}")
        print("(expected until keyframe production runs; gate and preview share the registry)")
        return 3

    total = sum(item["seconds"] for item in plan)
    if args.plan_only:
        for item in plan:
            print(f"{item['shot_id']:<18} {item['seconds']:>5.1f}s  {Path(item['image']).name}")
        print(f"total: {total:.1f}s over {len(plan)} moments")
        return 0

    cmd = ffmpeg_cmd(plan, args.out, args.audio)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=OUT_DIR)
    if result.returncode:
        print(result.stderr[-2000:])
        return 4
    print(f"preview: {args.out} ({total:.1f}s, {len(plan)} moments, audio={'yes' if args.audio else 'silent'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
