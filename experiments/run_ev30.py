"""Run the EV 30s ad segments after user creative approval.

Hard rule: zero RunningHub calls unless every segment contract carries
user_script_review status=approved with a non-empty reviewed_by.
Best-of-N is supported per segment (S2 tracking defaults to 2 takes).
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

from shortfilm.prompt_contract import compile_minimax_prompt, validate_director_contract
from shortfilm.rh_adapter import render_packet
from shortfilm.cli.normalize_video import normalize

CONTRACT_DIR = ROOT / "examples/ev30"
OUT = ROOT / "output/ev30"


def load_contracts() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(CONTRACT_DIR.glob("s*.json"))]


def approval_errors(contracts: list[dict]) -> list[str]:
    errors = []
    for doc in contracts:
        rev = doc.get("user_script_review", {})
        sid = doc.get("segment_id", "unknown")
        if rev.get("status") != "approved":
            errors.append(f"{sid}: approval status={rev.get('status')!r}, expected 'approved'")
        elif not str(rev.get("reviewed_by", "")).strip():
            errors.append(f"{sid}: approved contract missing reviewed_by")
    return errors


def main(best_of: dict[str, int] | None = None) -> int:
    best_of = best_of or {}
    contracts = load_contracts()
    if not contracts:
        print("no contracts found in", CONTRACT_DIR); return 1
    errors = approval_errors(contracts)
    if errors:
        print("REFUSED — user creative approval missing:")
        for e in errors: print("  -", e)
        print("Render blocked by design. Ask the user to approve/revise the proposal first.")
        return 2
    manifest = OUT / "render/asset_manifest.json"
    by: dict[str, dict] = {}
    if manifest.exists():
        by = {x["shot_id"]: x for x in json.loads(manifest.read_text(encoding="utf-8")).get("results", [])}
    for doc in contracts:
        sid = doc.get("segment_id") or doc["user_script_review"]["script_version"]
        prompt = compile_minimax_prompt(doc)
        takes = best_of.get(sid, 1)
        for take in range(1, takes + 1):
            shot_id = sid if takes == 1 else f"{sid}_T{take}"
            if by.get(shot_id, {}).get("status") == "success": continue
            try:
                r = render_packet({"shot_id": shot_id, "duration": float(doc["duration"]),
                                   "prompt": prompt}, OUT / "render/shots", workflow="t2v",
                                  poll=10, max_wait=1200)
                vertical = []
                for raw in r.get("outputs", []):
                    src = Path(raw); dst = src.with_name(src.stem + "_vertical.mp4")
                    normalize(src, dst, focus=.38); vertical.append(str(dst))
                r["raw_outputs"] = r.get("outputs", []); r["outputs"] = vertical
            except Exception as exc:
                r = {"shot_id": shot_id, "status": "failed", "error": str(exc)}
            by[shot_id] = r
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text(json.dumps({"project": "ev30", "results": list(by.values())},
                                           ensure_ascii=False, indent=2), encoding="utf-8")
            print(shot_id, r.get("status"), r.get("task_id", ""), r.get("error", ""), flush=True)
    return 1 if any(x.get("status") == "failed" for x in by.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main({"S2_silent_flow": 2}))
