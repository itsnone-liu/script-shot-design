"""Run the approved 12s multi-shot drink container on variable-duration T2V.

The runner is intentionally inert until the direct human approval is written
into the contract. It then renders serial takes and persists a resumable
manifest for cut/camera QA.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from shortfilm.prompt_contract import compile_minimax_prompt,validate_director_contract
from shortfilm.rh_adapter import render_packet

CONTRACT=ROOT/'examples/script_first/drink_high_variation_v1.json'
OUT=ROOT/'output/script_first/drink_high_variation_v1'

def load_contract()->dict:return json.loads(CONTRACT.read_text(encoding='utf-8'))
def approval_error(doc:dict)->str:
    r=doc.get('user_script_review') or {}
    if r.get('status')!='approved':return f"status={r.get('status')!r}, expected 'approved'"
    if not str(r.get('script_version','')).strip():return 'missing script_version'
    if not str(r.get('reviewed_by','')).strip():return 'missing reviewed_by'
    return ''

def main(takes:int=2)->int:
    doc=load_contract();err=approval_error(doc)
    if err:
        print('REFUSED — direct user script approval required:',err)
        return 2
    errors=validate_director_contract(doc)
    if errors:
        print('CONTRACT INVALID:',*errors,sep='\n- ');return 3
    prompt=compile_minimax_prompt(doc);manifest=OUT/'asset_manifest.json';by={}
    if manifest.exists():by={x['shot_id']:x for x in json.loads(manifest.read_text(encoding='utf-8')).get('results',[])}
    for i in range(1,takes+1):
        sid=f'DRINK12_T{i}'
        if by.get(sid,{}).get('status')=='success':continue
        try:r=render_packet({'shot_id':sid,'duration':doc['duration'],'prompt':prompt,'aspect_ratio':'16:9 (Widescreen)'},OUT/'shots',workflow='t2v_variable',poll=10,max_wait=1500)
        except Exception as exc:r={'shot_id':sid,'status':'failed','error':str(exc)}
        by[sid]=r;manifest.parent.mkdir(parents=True,exist_ok=True);manifest.write_text(json.dumps({'contract':str(CONTRACT),'workflow_profile':'t2v_variable','results':list(by.values())},ensure_ascii=False,indent=2),encoding='utf-8');print(sid,r.get('status'),r.get('task_id',''),r.get('error',''),flush=True)
    return 1 if any(x.get('status')=='failed' for x in by.values()) else 0

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--takes',type=int,default=2);a=ap.parse_args();raise SystemExit(main(max(1,a.takes)))
