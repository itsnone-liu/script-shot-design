"""CLI for the provider-neutral 821 story pipeline."""
from __future__ import annotations
import argparse, json, os, shutil, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from validators import validate_package, validate_document, status
from stages import STAGES, messages_for
from llm.mock import MockClient
from llm.openai_compat import OpenAICompatibleClient

ROOT=Path(__file__).resolve().parent

def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def dump(path,data): Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="command",required=True)
    run=sub.add_parser("run"); run.add_argument("--brief",required=True); run.add_argument("--out",required=True); run.add_argument("--fixture-dir"); run.add_argument("--reference",default="{}"); run.add_argument("--rules",default="[]"); run.add_argument("--base-url",default=os.getenv("EIGHT21_LLM_URL","https://api.deepseek.com/v1/chat/completions")); run.add_argument("--model",default=os.getenv("EIGHT21_LLM_MODEL","deepseek-chat")); run.add_argument("--api-key",default=os.getenv("EIGHT21_LLM_API_KEY",os.getenv("OPENAI_API_KEY","")))
    args=ap.parse_args()
    if args.command=="run":
        out=Path(args.out); out.mkdir(parents=True,exist_ok=True); brief=load(args.brief)
        dump(out/"creative_brief.json",brief)
        if args.fixture_dir: client=MockClient(Path(args.fixture_dir))
        else: client=OpenAICompatibleClient(args.base_url,args.api_key,args.model)
        started=time.time(); package={}
        reference=load(args.reference) if args.reference!="{}" else {}; rules=load(args.rules) if args.rules!="[]" else []
        for stage in STAGES:
            stage_errors=[]
            for attempt in range(2):
                messages=messages_for(stage, brief, package, reference, rules, stage_errors)
                try: value=client.complete(messages,{"type":"object"},stage=stage)
                except FileNotFoundError: value=package.get(stage,{})
                stage_errors=validate_document(value, stage) if isinstance(value, dict) and stage != "script_markdown" else []
                if not stage_errors: break
            package[stage]=value
        issues=validate_package(package,brief); diagnostics={"status":status(issues),"issues":issues,"elapsed_sec":round(time.time()-started,2),"stages":list(STAGES)}; package["diagnostics"]=diagnostics
        for key,value in package.items():
            if key=="script_markdown":
                text = value.get("markdown", "") if isinstance(value, dict) else str(value)
                (out/"script.md").write_text(text,encoding="utf-8")
            elif key not in ("diagnostics",): dump(out/f"{key}.json",value)
        dump(out/"diagnostics.json",diagnostics); print(json.dumps(diagnostics,ensure_ascii=False,indent=2)); return 1 if diagnostics["status"]=="block" else 0

if __name__=="__main__": raise SystemExit(main())
