"""Assemble the EV 30s vertical master from rendered segment takes.

Usage:
  python experiments/assemble_ev30.py --s2 S2_silent_flow_T1
  python experiments/assemble_ev30.py --end-card-text "电，一线之光"

Hard cuts between matched-state segments, final fade to black, optional end card.
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/ev30"
FONT = "C\\:/Windows/Fonts/msyh.ttc"


def pick(manifest: dict, sid: str, override: str = "", landscape: bool = False) -> Path:
    results = {x["shot_id"]: x for x in manifest.get("results", [])}
    key = override or sid
    if key not in results or results[key].get("status") != "success":
        sys.exit(f"missing successful take for {key}")
    pool = results[key].get("raw_outputs", []) if landscape else [
        p for p in results[key].get("outputs", []) if p.endswith("_vertical.mp4")]
    if not pool: sys.exit(f"no {'raw' if landscape else 'vertical'} output for {key}")
    return Path(pool[0])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--s1", default="S1_static_energy")
    ap.add_argument("--s2", default="S2_silent_flow")
    ap.add_argument("--s3", default="S3_answer_of_lights")
    ap.add_argument("--end-card-text", default="")
    ap.add_argument("--hold", type=float, default=1.6, help="end card hold seconds")
    ap.add_argument("--landscape", action="store_true",
                    help="assemble from raw 1504x864 takes instead of 864x1536 vertical crops")
    args = ap.parse_args()

    w, h = (1504, 864) if args.landscape else (864, 1536)
    suffix = "_landscape" if args.landscape else ""
    manifest = json.loads((OUT / "render/asset_manifest.json").read_text(encoding="utf-8"))
    clips = [pick(manifest, "S1", args.s1, args.landscape),
             pick(manifest, "S2", args.s2, args.landscape),
             pick(manifest, "S3", args.s3, args.landscape)]
    concat_list = OUT / f"render/concat{suffix}.txt"
    concat_list.write_text("".join(f"file '{c.as_posix()}'\n" for c in clips), encoding="utf-8")
    master = OUT / f"ev30_30s_master{suffix}.mp4"
    hold = max(args.hold, 1.0)
    fontsize = 72 if args.landscape else 54
    def dur(p: Path) -> float:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", str(p)], check=True, capture_output=True, text=True)
        return float(r.stdout.strip())
    total = sum(dur(c) for c in clips) + hold
    fade_st = max(total - 0.6, 0.0)
    tail = (f"color=c=black:s={w}x{h}:d={hold:g}:r=24,format=yuv420p[v1];"
            f"[v0][v1]concat=n=2:v=1:a=0[v]")
    if args.end_card_text:
        escaped = args.end_card_text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        tail = (f"color=c=black:s={w}x{h}:d={hold:g}:r=24,drawtext=fontfile='{FONT}':"
                f"text='{escaped}':fontcolor=white:fontsize={fontsize}:x=(w-text_w)/2:y=(h-text_h)/2,"
                f"format=yuv420p[v1];[v0][v1]concat=n=2:v=1:a=0[v]")
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
           "-filter_complex",
           f"[0:v]fps=24,scale={w}:{h},format=yuv420p[v0];{tail};[v]fade=t=out:st={fade_st:g}:d=0.6[vout]",
           "-map", "[vout]", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
           "-movflags", "+faststart", str(master)]
    subprocess.run(cmd, check=True, capture_output=True)
    print("master:", master)


if __name__ == "__main__":
    main()
