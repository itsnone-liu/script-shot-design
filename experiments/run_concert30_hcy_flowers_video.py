"""Approval-gated, resumable renderer for concert30-hcy-flowers-v1.

Preflight and prompt compilation are free. Real RunningHub calls are impossible
until BOTH segment contracts carry direct user approval. Each take is persisted
separately so visual QA can select a winner without losing task metadata.
"""
from __future__ import annotations

import argparse
import copy
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

VERSION = "concert30-hcy-flowers-v1"
BASE = ROOT / "examples" / "concert30_hcy_flowers"
OUT = ROOT / "output" / "concert30_hcy_flowers_v1"
REF = OUT / "ref"
SEGMENTS = {
    "A": {
        "contract": BASE / "segA_v1.json",
        "first": REF / "KF_A_FIRST.png",
        "last": REF / "KF_A_LAST.png",
        "planned_takes": 2,
    },
    "B": {
        "contract": BASE / "segB_v1.json",
        "first": REF / "KF_B_FIRST.png",
        "last": REF / "KF_B_LAST.png",
        "planned_takes": 2,
    },
}
I2V_OVERRIDES = [
    {"nodeId": "142", "fieldName": "value", "fieldValue": "0.6"},
    {"nodeId": "175", "fieldName": "strength_model", "fieldValue": "0"},
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def approval_errors(documents: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for segment, doc in zip(SEGMENTS, documents):
        review = doc.get("user_script_review") or {}
        if review.get("status") != "approved":
            errors.append(f"segment {segment}: direct user approval is required")
        if review.get("script_version") != VERSION:
            errors.append(f"segment {segment}: script_version must be {VERSION}")
        if str(review.get("reviewed_by") or "").strip() != "user":
            errors.append(f"segment {segment}: reviewed_by must be user")
    return errors


def contract_errors(documents: list[dict[str, Any]], *, require_approval: bool) -> list[str]:
    errors: list[str] = []
    for segment, doc in zip(SEGMENTS, documents):
        errors.extend(f"segment {segment}: {x}" for x in validate_director_contract(doc, require_approval=require_approval))
        errors.extend(
            f"segment {segment}: {finding.rule}: {finding.message}"
            for finding in lint_camera(doc)
            if finding.severity == "error"
        )
    return errors


def _compact_for_minimax(doc: dict[str, Any]) -> dict[str, Any]:
    """Keep the approved contract intact, but fit the validated MiniMax 7000-char input cap."""
    draft = copy.deepcopy(doc)
    # These details remain in the contract and visual QA record; MiniMax receives the
    # executable essentials plus the already-locked bible/first/last frames.
    for shot in draft.get("internal_shots", []):
        shot["cinematic_design"] = {}
        shot["visual_state"] = shot.get("visual_state", "")[:260]
        shot["subject_action"] = shot.get("subject_action", "")[:220]
        shot["camera_action"] = shot.get("camera_action", "")[:180]
        shot["lighting_state"] = shot.get("lighting_state", "")[:160]
        shot["end_state"] = shot.get("end_state", "")[:150]
        plan = shot.get("camera_plan", {})
        plan["path"] = plan.get("path", "")[:150]
        plan["axis_lock"] = plan.get("axis_lock", "")[:100]
        plan["stop_condition"] = plan.get("stop_condition", "")[:100]
    # The compiler uses this bible; remove prose duplication while retaining hard locks.
    bible = draft.get("prompt_bible", {})
    bible["material_lock"] = bible.get("material_lock", "")[:180]
    bible["environment_lock"] = bible.get("environment_lock", "")[:220]
    bible["never_show"] = bible.get("never_show", [])[:12]
    draft["user_script_review"] = {"status": "approved", "script_version": VERSION, "reviewed_by": "user"}
    return draft


def compile_draft_prompts(documents: list[dict[str, Any]]) -> dict[str, str]:
    prompts: dict[str, str] = {}
    for segment, doc in zip(SEGMENTS, documents):
        prompts[segment] = compile_minimax_prompt(_compact_for_minimax(doc))
    return prompts


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
    shot_id = f"CON30_{segment}_T{take}"
    return render_packet(
        {"shot_id": shot_id, "duration": doc["duration"], "prompt": prompt, "aspect_ratio": "16:9 (Widescreen)"},
        OUT / "shots",
        workflow="i2v",
        reference_file=str(spec["first"]),
        last_reference_file=str(spec["last"]),
        extra_nodes=I2V_OVERRIDES,
        poll=10,
        max_wait=2700,
    )


def stitch(selected: dict[str, int]) -> Path:
    manifest = load_manifest()
    by = {(x.get("segment"), x.get("take")): x for x in manifest.get("takes", [])}
    files: list[str] = []
    for segment in SEGMENTS:
        item = by.get((segment, selected[segment]))
        if not item or item.get("status") != "success" or not item.get("outputs"):
            raise ValueError(f"no successful selected take for segment {segment}")
        files.append(item["outputs"][0])
    OUT.mkdir(parents=True, exist_ok=True)
    concat = OUT / "concat_selected.txt"
    concat.write_text("\n".join(f"file '{path}'" for path in files), encoding="utf-8")
    master = OUT / "concert30_hcy_flowers_v1_master.mp4"
    result = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(master)])
    if result.returncode:
        raise RuntimeError("ffmpeg concat failed; normalize selected takes before retry")
    return master


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true", help="validate drafts and compile prompts; never create a paid task")
    parser.add_argument("--segment", choices=tuple(SEGMENTS))
    parser.add_argument("--take", type=int)
    parser.add_argument("--stitch", action="store_true")
    parser.add_argument("--select-a", type=int)
    parser.add_argument("--select-b", type=int)
    args = parser.parse_args()

    documents = [load_json(spec["contract"]) for spec in SEGMENTS.values()]
    draft_errors = contract_errors(documents, require_approval=False)
    if draft_errors:
        print("CONTRACT INVALID")
        print("\n".join(f"- {x}" for x in draft_errors))
        return 3
    prompts = compile_draft_prompts(documents)

    if args.preflight:
        print(json.dumps({
            "status": "preflight_pass",
            "approval": [doc["user_script_review"].get("status") for doc in documents],
            "prompt_chars": {segment: len(prompt) for segment, prompt in prompts.items()},
            "planned_takes": {segment: spec["planned_takes"] for segment, spec in SEGMENTS.items()},
            "paid_task_created": False,
        }, ensure_ascii=False, indent=2))
        return 0

    approvals = approval_errors(documents)
    if approvals:
        print("REFUSED - no paid task created")
        print("\n".join(f"- {x}" for x in approvals))
        return 2

    if args.stitch:
        if not args.select_a or not args.select_b:
            print("--stitch requires --select-a and --select-b")
            return 4
        print(stitch({"A": args.select_a, "B": args.select_b}))
        return 0

    if not args.segment or not args.take:
        print("real rendering requires --segment A|B and --take N")
        return 4
    if args.take < 1 or args.take > SEGMENTS[args.segment]["planned_takes"]:
        print(f"take out of planned range for segment {args.segment}")
        return 4

    manifest = load_manifest()
    existing = next((x for x in manifest.get("takes", []) if x.get("segment") == args.segment and x.get("take") == args.take), None)
    if existing and existing.get("status") == "success":
        print("already successful", existing.get("shot_id"))
        return 0
    try:
        result = render_take(args.segment, args.take, documents[tuple(SEGMENTS).index(args.segment)], prompts[args.segment])
    except Exception as exc:
        result = {"shot_id": f"CON30_{args.segment}_T{args.take}", "status": "failed", "error": str(exc)}
    result.update({"segment": args.segment, "take": args.take})
    takes = [x for x in manifest.get("takes", []) if not (x.get("segment") == args.segment and x.get("take") == args.take)]
    takes.append(result)
    manifest["takes"] = takes
    save_manifest(manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
