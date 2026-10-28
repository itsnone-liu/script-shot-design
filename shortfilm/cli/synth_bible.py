"""Synthesize a seg prompt_bible from asset cards (ASSET_STORYBOARD_SCHEMA_V1 §4).

Usage (from repo root):
  python -m shortfilm.cli.synth_bible \
      --cards examples/creative_v2/asset_cards_couple30_v1.json \
      --cast char_woman,char_man --scene scene_bedroom \
      --staging examples/creative_v2/couple30_segA_staging_v1.json \
      --check examples/creative_v2/couple30_segA_v1.json

Modes:
  default   print the synthesized prompt_bible JSON (optionally --out FILE)
  --check   cross-check a legacy seg's hand-written prompt_bible against the
            synthesis; exit 1 on errors (must-fix), report diffs (card gaps)
  --refs-manifest  write content hashes for every card's reference chain
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from shortfilm.assets import (
    build_refs_manifest,
    crosscheck_bible,
    load_asset_cards,
    synth_prompt_bible,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cards", type=Path, required=True, help="asset cards JSON (comma-separated for multiple files)")
    ap.add_argument("--cast", default="", help="comma-separated character card ids")
    ap.add_argument("--scene", required=True, help="scene card id")
    ap.add_argument("--props", default="", help="comma-separated prop card ids")
    ap.add_argument("--staging", type=Path, default=None, help="seg staging extras JSON")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--check", type=Path, default=None, help="legacy seg JSON to diff against")
    ap.add_argument("--refs-root", type=Path, default=None, help="identity root for refs manifest")
    ap.add_argument("--refs-manifest", type=Path, default=None, help="write refs hash manifest here")
    args = ap.parse_args()

    from shortfilm.assets import load_cards_files

    cards = load_cards_files([Path(x.strip()) for x in str(args.cards).split(",") if x.strip()])
    cast = [x.strip() for x in args.cast.split(",") if x.strip()]
    props = [x.strip() for x in args.props.split(",") if x.strip()]
    staging = json.loads(args.staging.read_text(encoding="utf-8")) if args.staging else {}

    if args.refs_manifest:
        if not args.refs_root:
            print("--refs-manifest requires --refs-root")
            return 1
        manifest = build_refs_manifest(args.cards, args.refs_root)
        args.refs_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"refs manifest written: {args.refs_manifest} ({len(manifest['cards'])} cards)")
        if not args.check and not args.out:
            return 0

    if args.check:
        seg = json.loads(args.check.read_text(encoding="utf-8"))
        report = crosscheck_bible(seg, cards, cast, args.scene, staging, prop_ids=props)
        for err in report["errors"]:
            print(f"ERROR {err}")
        for diff in report["diffs"]:
            print(f"DIFF  {diff}")
        for note in report["info"]:
            print(f"info  {note}")
        print(f"errors={len(report['errors'])} diffs={len(report['diffs'])} info={len(report['info'])}")
        if args.out:
            args.out.write_text(json.dumps(report["synthesized"], ensure_ascii=False, indent=2), encoding="utf-8")
        return 1 if report["errors"] else 0

    bible = synth_prompt_bible(cards, cast, args.scene, staging, prop_ids=props)
    text = json.dumps(bible, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"synthesized prompt_bible written: {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
