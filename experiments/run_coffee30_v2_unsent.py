"""Approval-gated, resumable renderer for coffee30 v2《未发送》(unsent).

v2 differences from the C1 runner (run_coffee30_dont_wake_her.py):

1. Keyframe pay-gate is the REGISTRY (shortfilm/keyframe_gate.py): every
   container task requires first/last keyframes that are user-approved AND
   sha256-matched — closing the C1-era process-convention gap. first_frame
   declarations in the segs map to reference_file / last_reference_file here.
2. check_seg parity: contract + camera lint + shot extensions all validated
   through the same entry points the preflight CLI uses.
3. Two-pass design (phase-0 两遍法): identical compiled prompts and model;
   pass 1 = baseline practice (single take per container, no instrument
   checks); pass 2 = enhanced (N takes per container + five-point keyframe
   readiness checklist required). Pass is recorded on every take.
4. Cost ledger: every paid call (success, failure, refusal) is appended to
   cost_ledger.jsonl — 预算无上限 but 记账无条件.

Preflight/packet-build is free (--dry). Real RunningHub calls are impossible
until: seg user_script_review=approved(user) AND registry approval=approved
with matching sha256 for all six container keyframes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shortfilm.camera_lint import lint_camera
from shortfilm.keyframe_gate import gate_errors, load_registry
from shortfilm.prompt_contract import compile_minimax_prompt, validate_director_contract
from shortfilm.rh_adapter import render_packet
from shortfilm.shot_extensions import validate_shot_extensions

VERSION = "coffee30-v2-director-v2"
BASE = ROOT / "examples" / "creative_v2"
OUT = ROOT / "output" / "creative_v2" / "coffee30_v2_unsent"
REGISTRY_PATH = OUT / "keyframes_registry_v1.json"
PLAN_PATH = BASE / "coffee30_v2_unsent_production_plan_v1.json"
LEDGER_PATH = OUT / "cost_ledger.jsonl"
I2V_OVERRIDES = [
    {"nodeId": "142", "fieldName": "value", "fieldValue": "0.6"},
    {"nodeId": "175", "fieldName": "strength_model", "fieldValue": "0"},
]
PASSES = {  # takes per container per pass (phase-0 两遍法 lock)
    1: {"label": "baseline", "takes": 1, "checklist_required": False},
    2: {"label": "enhanced", "takes": 2, "checklist_required": True},
}
CHECKLIST_PATH = OUT / "keyframe_readiness_checklist.json"
SEGMENTS = {
    "A": {"contract": BASE / "coffee30_v2_segA_v1.json"},
    "B": {"contract": BASE / "coffee30_v2_segB_v1.json"},
    "C": {"contract": BASE / "coffee30_v2_segC_v1.json"},
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def cards_for(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    from shortfilm.assets import load_cards_files

    paths = [ROOT / str(p) for p in doc["asset_refs"]["cards_path"]]
    return load_cards_files(paths)


def contract_errors(documents: dict[str, dict[str, Any]], *, require_approval: bool) -> list[str]:
    errors: list[str] = []
    for segment, doc in documents.items():
        cards = cards_for(doc)
        errors.extend(f"segment {segment}: {x}" for x in validate_director_contract(doc, require_approval=require_approval, cards=cards))
        errors.extend(
            f"segment {segment}: {finding.rule}: {finding.message}"
            for finding in lint_camera(doc)
            if finding.severity == "error"
        )
        errors.extend(f"segment {segment}: EXT {x}" for x in validate_shot_extensions(doc, cards=cards))
    return errors


def production_errors() -> list[str]:
    """Fail closed on pending design synchronization and production approval."""
    errors: list[str] = []
    design_path = BASE / "coffee30_v2_design_review.json"
    for label, path in (("design package", design_path), ("production plan", PLAN_PATH)):
        if not path.is_file():
            errors.append(f"{label}: approval record missing")
            continue
        record = load_json(path)
        expected = "ready" if label == "design package" else "approved"
        if record.get("status") != expected or record.get("approved_by") != "user":
            errors.append(f"{label}: requires status={expected} and approved_by=user")
    return errors


def approval_errors(documents: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for segment, doc in documents.items():
        review = doc.get("user_script_review") or {}
        if review.get("status") != "approved":
            errors.append(f"segment {segment}: direct user script approval is required")
        if review.get("script_version") != VERSION:
            errors.append(f"segment {segment}: script_version must be {VERSION}")
        if str(review.get("reviewed_by") or "").strip() != "user":
            errors.append(f"segment {segment}: reviewed_by must be user")
    return errors


def registry_errors(documents: dict[str, dict[str, Any]]) -> list[str]:
    """All three containers gated by one registry: user-approved + sha256 match."""
    if not REGISTRY_PATH.exists():
        return [f"keyframe registry missing: {REGISTRY_PATH}"]
    registry = load_registry(REGISTRY_PATH)
    errors: list[str] = []
    for segment, doc in documents.items():
        errors.extend(f"segment {segment}: GATE {x}" for x in gate_errors(doc, registry, registry_path=REGISTRY_PATH))
        endpoint = {"internal_shots": [{"shot_id": f"{segment}_container_end", "first_frame": {
            "keyframe_id": f"KF_V2_{segment}_LAST", "approval": "approved"}}]}
        errors.extend(f"segment {segment}: ENDPOINT {x}" for x in gate_errors(endpoint, registry, registry_path=REGISTRY_PATH))
    return errors


def compile_prompts(documents: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Compile with the REAL review blocks (call only after approvals+gate)."""
    return {segment: compile_minimax_prompt(doc, cards=cards_for(doc)) for segment, doc in documents.items()}


def ledger_append(event: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    event["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with LEDGER_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _registry_file(entry: dict[str, Any]) -> Path:
    """Registry file paths are relative to the registry JSON itself."""
    path = Path(str(entry["file"]))
    return path if path.is_absolute() else REGISTRY_PATH.parent / path


def reference_paths(doc: dict[str, Any], segment: str) -> tuple[str, str]:
    """first_frame declarations -> container reference_map (registry is truth).

    Container first frame = first shot's approved keyframe; container last
    frame = the dedicated KF_V2_<seg>_LAST entry (end state of the final shot).
    """
    registry = load_registry(REGISTRY_PATH)
    first_id = doc["internal_shots"][0]["first_frame"]["keyframe_id"]
    last_id = f"KF_V2_{segment}_LAST"
    by_id = registry["keyframes"]
    return str(_registry_file(by_id[first_id])), str(_registry_file(by_id[last_id]))


def render_take(pass_id: int, segment: str, take: int, doc: dict[str, Any], prompt: str, dry: bool) -> dict[str, Any]:
    first, last = reference_paths(doc, segment)
    shot_id = f"UNSENT_P{pass_id}_{segment}_T{take}"
    packet = {"shot_id": shot_id, "duration": doc["duration"], "prompt": prompt, "aspect_ratio": "16:9 (Widescreen)"}
    return render_packet(
        packet, OUT / "shots", workflow="i2v",
        reference_file=first, last_reference_file=last,
        extra_nodes=I2V_OVERRIDES, dry_run=dry, poll=10, max_wait=2700,
    )


def checklist_errors() -> list[str]:
    """Pass-2 tripwire: the five-point readiness checklist must exist AND be
    fully checked — an empty/unchecked template must NOT unlock paid calls."""
    if not CHECKLIST_PATH.exists():
        return [f"pass 2 requires the five-point keyframe readiness checklist: {CHECKLIST_PATH}"]
    try:
        checklist = load_json(CHECKLIST_PATH)
    except Exception as exc:  # noqa: BLE001
        return [f"checklist unreadable: {exc}"]
    errors: list[str] = []
    entries = checklist.get("entries") or []
    if not entries:
        return ["checklist has no entries"]
    for entry in entries:
        kid = entry.get("keyframe_id", "?")
        for item in ("information", "identity_styling", "spatial", "action_ready", "continuity"):
            if entry.get("items", {}).get(item) is not True:
                errors.append(f"checklist: {kid} item '{item}' not checked")
    return errors


def load_manifest() -> dict[str, Any]:
    path = OUT / "asset_manifest.json"
    return load_json(path) if path.exists() else {"version": VERSION, "takes": []}


def save_manifest(manifest: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "asset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def stitch(pass_id: int, selected: dict[str, int]) -> Path:
    manifest = load_manifest()
    by = {(x.get("pass"), x.get("segment"), x.get("take")): x for x in manifest.get("takes", [])}
    files: list[str] = []
    for segment in SEGMENTS:
        item = by.get((pass_id, segment, selected[segment]))
        if not item or item.get("status") != "success" or not item.get("outputs"):
            raise ValueError(f"no successful selected take for pass {pass_id} segment {segment}")
        files.append(item["outputs"][0])
    concat = OUT / f"concat_p{pass_id}.txt"
    concat.write_text("\n".join(f"file '{path}'" for path in files), encoding="utf-8")
    master = OUT / f"coffee30_v2_unsent_p{pass_id}_master.mp4"
    result = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(master)])
    if result.returncode:
        raise RuntimeError("ffmpeg concat failed; normalize selected takes before retry")
    return master


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true", help="free: validate drafts, prompts, registry; never create a paid task")
    parser.add_argument("--dry", action="store_true", help="build render packets without creating paid tasks")
    parser.add_argument("--hash-registry", action="store_true", help="fill sha256 for registry entries whose files exist (no approval change)")
    parser.add_argument("--pass", dest="pass_id", type=int, choices=(1, 2))
    parser.add_argument("--segment", choices=tuple(SEGMENTS))
    parser.add_argument("--take", type=int)
    parser.add_argument("--stitch", action="store_true")
    parser.add_argument("--select", type=int, action="append", help="selected take per segment in A,B,C order")
    args = parser.parse_args()

    documents = {segment: load_json(spec["contract"]) for segment, spec in SEGMENTS.items()}

    if args.hash_registry:
        registry = load_json(REGISTRY_PATH)
        for keyframe_id, entry in registry.get("keyframes", {}).items():
            path = _registry_file(entry)
            if path.is_file() and not entry.get("sha256"):
                entry["sha256"] = sha256_of(path)
                print(f"hashed {keyframe_id} -> {entry['sha256'][:16]}…")
        REGISTRY_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"registry updated: {REGISTRY_PATH}")
        return 0

    draft_errors = contract_errors(documents, require_approval=False)
    if draft_errors:
        print("CONTRACT INVALID")
        print("\n".join(f"- {x}" for x in draft_errors))
        return 3

    if args.preflight:
        plan = load_json(PLAN_PATH) if PLAN_PATH.exists() else {}
        gate = registry_errors(documents)
        report = {
            "status": "preflight_pass" if not gate else "preflight_pass_gate_pending",
            "script_approval": {segment: doc["user_script_review"].get("status") for segment, doc in documents.items()},
            "gate_errors": gate,
            "planned_paid_calls": plan.get("container_budget", {}).get("estimated_paid_calls_total"),
            "paid_task_created": False,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        ledger_append({"event": "preflight", "status": report["status"], "gate_errors": len(gate)})
        return 0

    approvals = approval_errors(documents) + production_errors()
    gates = registry_errors(documents)
    if approvals or gates:
        print("REFUSED - no paid task created")
        for err in [*approvals, *gates]:
            print(f"- {err}")
        ledger_append({"event": "refusal", "approvals": len(approvals), "gates": len(gates),
                       "detail": approvals + gates})
        return 2

    prompts = compile_prompts(documents)
    if args.dry:
        targets = (args.segment,) if args.segment else tuple(SEGMENTS)
        packets = [render_take(args.pass_id or 1, segment, 1, documents[segment], prompts[segment], dry=True)
                   for segment in targets]
        print(json.dumps({"status": "dry-run", "packets": [p["shot_id"] for p in packets],
                          "nodes": [len(p["nodeInfoList"]) for p in packets]}, ensure_ascii=False, indent=2))
        return 0

    pass_cfg = PASSES[args.pass_id] if args.pass_id else None
    if args.stitch:
        if not args.select or len(args.select) != len(SEGMENTS):
            print("--stitch requires --select per segment in A,B,C order")
            return 4
        print(stitch(args.pass_id or 1, dict(zip(SEGMENTS, args.select))))
        return 0

    if not (args.pass_id and args.segment and args.take):
        print("real rendering requires --pass 1|2 --segment A|B|C --take N")
        return 4
    if args.take < 1 or args.take > pass_cfg["takes"]:
        print(f"take out of planned range for pass {args.pass_id} ({pass_cfg['takes']})")
        return 4
    if pass_cfg["checklist_required"] and checklist_errors():
        for err in checklist_errors():
            print(err)
        print(f"pass 2 requires ALL five-point readiness items checked: {CHECKLIST_PATH}")
        return 4

    manifest = load_manifest()
    existing = next((x for x in manifest.get("takes", [])
                     if x.get("pass") == args.pass_id and x.get("segment") == args.segment and x.get("take") == args.take), None)
    if existing and existing.get("status") == "success":
        print("already successful", existing.get("shot_id"))
        return 0

    try:
        result = render_take(args.pass_id, args.segment, args.take, documents[args.segment], prompts[args.segment], dry=False)
    except Exception as exc:  # noqa: BLE001 — failures must reach the ledger too
        result = {"shot_id": f"UNSENT_P{args.pass_id}_{args.segment}_T{args.take}", "status": "failed", "error": str(exc)}
    result.update({"pass": args.pass_id, "segment": args.segment, "take": args.take})
    takes = [x for x in manifest.get("takes", [])
             if not (x.get("pass") == args.pass_id and x.get("segment") == args.segment and x.get("take") == args.take)]
    takes.append(result)
    manifest["takes"] = takes
    save_manifest(manifest)
    ledger_append({"event": "paid_call", "shot_id": result["shot_id"], "status": result.get("status", "unknown"),
                   "task_id": result.get("task_id"), "prompt_chars": len(prompts[args.segment]),
                   "duration_s": documents[args.segment]["duration"]})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
