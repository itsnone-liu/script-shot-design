"""Run a targeted screenplay revision from an existing package and its reviews."""
from __future__ import annotations
import argparse, json, os, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from llm.openai_compat import OpenAICompatibleClient
from validators import validate_package, status, validate_document

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def dump(p,v): Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',required=True); ap.add_argument('--brief',required=True); ap.add_argument('--out',required=True); ap.add_argument('--reference',default='reference_zhihu.json'); ap.add_argument('--rules',default='shortfilm/knowledge/rules/candidate_rules_v0.1.json'); ap.add_argument('--timeout',type=int,default=180); ap.add_argument('--api-key',default=os.getenv('EIGHT21_LLM_API_KEY','')); ap.add_argument('--base-url',default=os.getenv('EIGHT21_LLM_URL','https://api.deepseek.com/v1/chat/completions')); ap.add_argument('--model',default=os.getenv('EIGHT21_LLM_MODEL','deepseek-chat')); args=ap.parse_args()
    src=Path(args.input); out=Path(args.out); out.mkdir(parents=True,exist_ok=True); brief=load(args.brief)
    package={}
    for name in ('concept_candidates','story_statement','beat_sheet','scene_cards','reviews'):
        p=src/f'{name}.json'
        if p.exists(): package[name]=load(p)
    script=(src/'script.md').read_text(encoding='utf-8') if (src/'script.md').exists() else ''
    package['script_markdown']={'markdown':script}
    reviews=package.get('reviews',{})
    prompt={
      'role':'senior screenplay revision room',
      'task':'Revise this short ad package using the review findings. Return one JSON object with story_statement, beat_sheet, scene_cards, script_markdown, revision_log, reviews.',
      'must_fix':[
        'replace any magical/glowing VFX discovery with a practical, pre-existing visual clue already present in the workspace',
        'make the emotional transition gradual: anxiety -> hesitation -> pause -> clearer judgment',
        'make the final result a concrete work submission, not a photo of a board',
        'keep one protagonist, one location if possible, no dialogue, 30 seconds, and MiniMax-friendly short segments',
        'all readable text and brand UI are post-production; do not rely on generated text',
        'product action no more than two times; product can remain a visual anchor without extra drinking',
      ],
      'brief':brief,'package':package,'reviews':reviews,
      'output_contract':{'story_statement':'object','beat_sheet':'object with beats list','scene_cards':'object with scenes list','script_markdown':'object with markdown string','revision_log':'object','reviews':'object'},
    }
    client=OpenAICompatibleClient(args.base_url,args.api_key,args.model,timeout=args.timeout)
    t=time.time(); result=client.complete([{'role':'system','content':'You are a precise screenplay editor. Return valid JSON only, no reasoning.'},{'role':'user','content':json.dumps(prompt,ensure_ascii=False)}],{'type':'object'},stage='revision')
    package.update(result)
    issues=validate_package(package,brief)
    diagnostics={'status':status(issues),'issues':issues,'elapsed_sec':round(time.time()-t,2),'revision_source':str(src)}
    package['diagnostics']=diagnostics
    for name in ('story_statement','beat_sheet','scene_cards','revision_log','reviews','diagnostics'):
        if name in package: dump(out/f'{name}.json',package[name])
    sm=package.get('script_markdown',{})
    (out/'script.md').write_text(sm.get('markdown','') if isinstance(sm,dict) else str(sm),encoding='utf-8')
    dump(out/'creative_brief.json',brief)
    print(json.dumps(diagnostics,ensure_ascii=False,indent=2)); return 1 if diagnostics['status']=='block' else 0
if __name__=='__main__': raise SystemExit(main())
