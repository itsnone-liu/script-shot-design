"""Validate a director contract and compile one MiniMax-ready prompt."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from shortfilm.prompt_contract import compile_minimax_prompt, validate_director_contract
from shortfilm.camera_lint import lint_camera


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("contract",type=Path)
    ap.add_argument("output",type=Path)
    ap.add_argument("--allow-unapproved",action="store_true",help="validation/draft only; never use for production export")
    args=ap.parse_args()
    doc=json.loads(args.contract.read_text(encoding="utf-8"))
    errors=validate_director_contract(doc,require_approval=not args.allow_unapproved)
    findings=lint_camera(doc)
    errors.extend(f"{f.rule}: {f.message}" for f in findings if f.severity=="error")
    for finding in findings:
        print(f"CAMERA LINT {finding.severity.upper()} {finding.rule}: {finding.message}")
    if errors:
        print("DIRECTOR CONTRACT BLOCKED")
        print("\n".join(f"- {x}" for x in errors))
        return 1
    if args.allow_unapproved:
        draft=dict(doc)
        draft["user_script_review"]={"status":"approved","script_version":"draft-validation","reviewed_by":"draft-only"}
        prompt=compile_minimax_prompt(draft)
    else: prompt=compile_minimax_prompt(doc)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(prompt,encoding="utf-8")
    print(f"COMPILED: {args.output}")
    return 0

if __name__=="__main__": raise SystemExit(main())
