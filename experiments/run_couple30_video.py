"""Approval-gated, resumable renderer for couple30 (C2 再睡五分钟) v1.

Segments A (14s, 3 takes), B (7s flip test, 4 takes), C (13s finale, 3 takes).
Preflight/compile free; paid i2v tasks run one at a time, resumable via manifest.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shortfilm.camera_lint import lint_camera
from shortfilm.prompt_contract import compile_minimax_prompt, validate_director_contract
from shortfilm.rh_adapter import render_packet

VERSION = "couple30-v1"
BASE = ROOT / "examples" / "creative_v2"
KF = ROOT / "examples" / "couple30_v1" / "keyframes"
OUT = ROOT / "output" / "creative_v2" / "couple30_v1"
SEGMENTS = {
    "A": {"contract": BASE / "couple30_segA_v1.json",
          "first": KF / "KF_A1_corrected.png", "last": KF / "KF_A_LAST_corrected.png",
          "planned_takes": 3},
    "B": {"contract": BASE / "couple30_segB_v1.json",
          "first": KF / "KF_A_LAST_corrected.png", "last": KF / "KF_B_LAST_corrected.png",
          "planned_takes": 4},
    "C": {"contract": BASE / "couple30_segC_v1.json",
          "first": KF / "KF_B_LAST_corrected.png", "last": KF / "KF_C_LAST_corrected.png",
          "planned_takes": 3},
}
I2V_OVERRIDES = [
    {"nodeId": "142", "fieldName": "value", "fieldValue": "0.6"},
    {"nodeId": "175", "fieldName": "strength_model", "fieldValue": "0"},
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def contract_errors(documents: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for seg, doc in documents.items():
        errors.extend(f"segment {seg}: {x}" for x in validate_director_contract(doc, require_approval=True))
        errors.extend(
            f"segment {seg}: {f.rule}: {f.message}"
            for f in lint_camera(doc) if f.severity == "error"
        )
    return errors


def compile_prompts(documents: dict[str, Any]) -> dict[str, str]:
    return {seg: compile_minimax_prompt(doc) for seg, doc in documents.items()}


def load_manifest() -> dict[str, Any]:
    path = OUT / "asset_manifest.json"
    return load_json(path) if path.exists() else {"version": VERSION, "takes": []}


def save_manifest(manifest: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "asset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def render_take(segment: str, take: int, doc: dict[str, Any], prompt: str) -> dict[str, Any]:
    spec = SEGMENTS[segment]
    for key in ("first", "last"):
        if not spec[key].exists():
            raise FileNotFoundError(f"missing {segment} {key} keyframe: {spec[key]}")
    shot_id = f"C30_{segment}_T{take}"
    return render_packet(
        {"shot_id": shot_id, "duration": doc["duration"], "prompt": prompt},
        OUT / "shots",
        workflow="i2v",
        reference_file=str(spec["first"]),
        last_reference_file=str(spec["last"]),
        extra_nodes=I2V_OVERRIDES,
        poll=15,
        max_wait=3000,
    )


def run_take(segment: str, take: int, documents, prompts) -> int:
    manifest = load_manifest()
    existing = next((x for x in manifest.get("takes", [])
                     if x.get("segment") == segment and x.get("take") == take), None)
    if existing and existing.get("status") == "success":
        print("already successful", existing.get("shot_id"))
        return 0
    try:
        result = render_take(segment, take, documents[segment], prompts[segment])
    except Exception as exc:
        result = {"shot_id": f"C30_{segment}_T{take}", "status": "failed", "error": str(exc)}
    result.update({"segment": segment, "take": take})
    takes = [x for x in manifest.get("takes", [])
             if not (x.get("segment") == segment and x.get("take") == take)]
    takes.append(result)
    manifest["takes"] = takes
    save_manifest(manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "success" else 1


def stitch(selected: dict[str, int]) -> Path:
    manifest = load_manifest()
    by = {(x.get("segment"), x.get("take")): x for x in manifest.get("takes", [])}
    files = []
    for segment in SEGMENTS:
        item = by.get((segment, selected[segment]))
        if not item or item.get("status") != "success" or not item.get("outputs"):
            raise ValueError(f"no successful selected take for segment {segment}")
        files.append(item["outputs"][0])
    OUT.mkdir(parents=True, exist_ok=True)
    concat = OUT / "concat_selected.txt"
    concat.write_text("\n".join(f"file '{p}'" for p in files), encoding="utf-8")
    master = OUT / "couple30_v1_master.mp4"
    result = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                             "-i", str(concat), "-c", "copy", str(master)])
    if result.returncode:
        raise RuntimeError("ffmpeg concat failed; normalize selected takes before retrying")
    return master


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--all", action="store_true", help="run every planned take sequentially, resumable")
    parser.add_argument("--segment", choices=tuple(SEGMENTS))
    parser.add_argument("--take", type=int)
    parser.add_argument("--stitch", action="store_true")
    parser.add_argument("--select", type=str, help="A:B:C take numbers, e.g. 1:2:1")
    args = parser.parse_args()

    documents = {seg: load_json(spec["contract"]) for seg, spec in SEGMENTS.items()}
    errors = contract_errors(documents)
    if errors:
        print("CONTRACT INVALID")
        print("\n".join(f"- {x}" for x in errors))
        return 3
    prompts = compile_prompts(documents)

    if args.preflight:
        print(json.dumps({
            "status": "preflight_pass",
            "durations": {s: documents[s]["duration"] for s in SEGMENTS},
            "prompt_chars": {s: len(p) for s, p in prompts.items()},
            "planned_takes": {s: SEGMENTS[s]["planned_takes"] for s in SEGMENTS},
            "total_paid_tasks": sum(SEGMENTS[s]["planned_takes"] for s in SEGMENTS),
        }, ensure_ascii=False, indent=2))
        return 0

    if args.stitch:
        if not args.select:
            print("--stitch requires --select A:B:C")
            return 4
        a, b, c = (int(x) for x in args.select.split(":"))
        print(stitch({"A": a, "B": b, "C": c}))
        return 0

    if args.all:
        failed = []
        for seg in SEGMENTS:
            for take in range(1, SEGMENTS[seg]["planned_takes"] + 1):
                print(f"\n===== {seg} take {take} =====", flush=True)
                if run_take(seg, take, documents, prompts) != 0:
                    failed.append((seg, take))
        print("FAILED_TAKES", failed if failed else "none")
        return 0

    if not args.segment or not args.take:
        print("use --preflight, --all, or --segment X --take N")
        return 4
    if args.take < 1 or args.take > SEGMENTS[args.segment]["planned_takes"]:
        print(f"take out of planned range for segment {args.segment}")
        return 4
    return run_take(args.segment, args.take, documents, prompts)


if __name__ == "__main__":
    raise SystemExit(main())
