"""Method-card lifecycle promoter (candidate → tested → verified).

The learning loop's write-back arm (方案 §7 证据/学习闭环): blind-review
evidence turns method cards from `candidate` into `tested` (single-piece
evidence) and later `verified` (cross-piece). Deterministic — no LLM. Every
promotion is journaled inside the card (evidence_refs + provenance line).

  python -m shortfilm.cli.methods_promote --list
  python -m shortfilm.cli.methods_promote --id method.expression-chain \
      --to tested --evidence "coffee30 v2 盲评：emotion轴 P2>P1 (form v1, seed 20261028)"

Downgrade is refused (verified is one-way per STORY_PIPELINE_UPGRADE rules;
corrections go through a new evidence entry, not silently rolling back).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ORDER = {"candidate": 0, "tested": 1, "verified": 2}
DEFAULT_DIR = Path(__file__).resolve().parents[1] / "knowledge" / "methods"


def _load(card_id: str, root: Path) -> tuple[Path, dict]:
    path = root / f"{card_id}.json"
    if not path.is_file():
        raise SystemExit(f"card not found: {path}")
    return path, json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--id", dest="card_id")
    ap.add_argument("--to", choices=("tested", "verified"))
    ap.add_argument("--evidence", help="evidence sentence recorded in evidence_refs")
    ap.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    args = ap.parse_args(argv)

    if args.list or not args.card_id:
        for path in sorted(args.dir.glob("method.*.json")):
            card = json.loads(path.read_text(encoding="utf-8"))
            print(f"{card['id']:<34} v{card.get('version', 0)}  {card.get('lifecycle', '?'):<9} evidence={len(card.get('evidence_refs', []))}")
        return 0

    if not args.to or not args.evidence:
        print("--to and --evidence are required for promotion")
        return 4
    path, card = _load(args.card_id, args.dir)
    current = card.get("lifecycle", "candidate")
    if ORDER[args.to] <= ORDER.get(current, 0):
        print(f"refused: {card['id']} is already {current}; lifecycle is forward-only")
        return 2

    card.setdefault("evidence_refs", []).append({
        "claim": args.evidence,
        "from": current,
        "to": args.to,
        "at": __import__("time").strftime("%Y-%m-%d"),
    })
    card["lifecycle"] = args.to
    card["version"] = int(card.get("version", 0)) + 1
    card.setdefault("provenance", []).append(
        {"source_id": "promotion", "locator": f"{current}->{args.to}: {args.evidence}"}
    )
    path.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"promoted {card['id']}: {current} -> {args.to} (v{card['version']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
