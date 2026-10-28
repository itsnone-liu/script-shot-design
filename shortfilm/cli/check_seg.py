"""Generic seg preflight: contract + camera lint + shot extensions + keyframe gate.

One entry point for the v2 flow (and a dryer for legacy segs):

  python -c "import sys; sys.path.insert(0, r'<repo>'); from shortfilm.cli.check_seg import main; sys.exit(main())" \
      --seg examples/creative_v2/coffee30_v2_segA_v1.json \
      --cards examples/creative_v2/asset_cards_couple30_v1.json \
      --keyframes output/creative_v2/coffee30_v2/keyframes.json

Exit 0 = safe to proceed to paid rendering (with user production approval);
exit 1 = blocking findings.  --draft drops the script-approval requirement so
pre-approval previews still preflight everything else.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from shortfilm.assets import load_asset_cards
from shortfilm.camera_lint import lint_camera
from shortfilm.keyframe_gate import gate_errors, load_registry
from shortfilm.prompt_contract import validate_director_contract
from shortfilm.shot_extensions import validate_shot_extensions


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seg", type=Path, required=True)
    ap.add_argument("--cards", type=Path, default=None, help="asset cards JSON (default: asset_refs.cards_path)")
    ap.add_argument("--keyframes", type=Path, default=None, help="keyframe registry JSON for the pay-gate")
    ap.add_argument("--draft", action="store_true", help="do not require script approval (pre-approval preview)")
    args = ap.parse_args()

    document = json.loads(args.seg.read_text(encoding="utf-8"))
    cards = None
    raw_cards_path = args.cards or (document.get("asset_refs") or {}).get("cards_path")
    cards_paths = [Path(str(x)) for x in raw_cards_path] if isinstance(raw_cards_path, list) else ([Path(str(raw_cards_path))] if raw_cards_path else [])
    if cards_paths:
        from shortfilm.assets import load_cards_files

        resolved = []
        for path in cards_paths:
            if not path.is_absolute():
                candidate = (Path(__file__).resolve().parents[2] / path) if (Path(__file__).resolve().parents[2] / path).is_file() else path
                path = candidate
            resolved.append(path)
        cards = load_cards_files(resolved)
        print(f"cards: {len(cards)} loaded from {len(resolved)} file(s)")

    blocking = 0
    contract_errors = validate_director_contract(document, require_approval=not args.draft, cards=cards)
    for err in contract_errors:
        print(f"CONTRACT {err}")
    blocking += len(contract_errors)

    lint_findings = [f for f in lint_camera(document) if f.severity == "error"]
    for finding in lint_findings:
        print(f"CAMERA  {finding.rule}: {finding.message}")
    blocking += len(lint_findings)

    extension_errors = validate_shot_extensions(document, cards=cards)
    for err in extension_errors:
        print(f"EXT     {err}")
    blocking += len(extension_errors)

    if args.keyframes:
        registry = load_registry(args.keyframes)
        gate = gate_errors(document, registry, registry_path=args.keyframes)
        for err in gate:
            print(f"GATE    {err}")
        blocking += len(gate)
    else:
        print("gate: skipped (no --keyframes registry supplied)")

    print(f"preflight: {'PASS' if blocking == 0 else f'BLOCKED ({blocking})'}")
    return 0 if blocking == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
