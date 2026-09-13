"""Render the approved coffee30 direction-1 film: two 15s script-first segments
stitched into a 30s master. Approval-gated exactly like the drink runner; the
15s stitch boundary is an external smash cut on action (A: brimming carafe ->
B: milk drop impact).
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from shortfilm.prompt_contract import compile_minimax_prompt,validate_director_contract
from shortfilm.rh_adapter import render_packet

SEGS=[(ROOT/'examples/script_first/coffee30_person_segA_v1.json','COFFEE30A'),
      (ROOT/'examples/script_first/coffee30_person_segB_v1.json','COFFEE30B')]
OUT=ROOT/'output/script_first/coffee30_person_v1'

def load(p:Path)->dict:return json.loads(p.read_text(encoding='utf-8'))
def approval_error(doc:dict)->str:
    r=doc.get('user_script_review') or {}
    if r.get('status')!='approved':return f"status={r.get('status')!r}, expected 'approved'"
    if not str(r.get('script_version','')).strip():return 'missing script_version'
    if not str(r.get('reviewed_by','')).strip():return 'missing reviewed_by'
    return ''

def main(takes:int=1)->int:
    manifest=OUT/'asset_manifest.json';by={}
    if manifest.exists():by={x['shot_id']:x for x in json.loads(manifest.read_text(encoding='utf-8')).get('results',[])}
    for i in range(1,takes+1):
        for contract,sid_base in SEGS:
            sid=f'{sid_base}_T{i}'
            if by.get(sid,{}).get('status')=='success':continue
            doc=load(contract);err=approval_error(doc)
            if err:print('REFUSED for',sid,'-',err);return 2
            errs=validate_director_contract(doc)
            if errs:print('CONTRACT INVALID for',sid,*errs,sep='\n- ');return 3
            prompt=compile_minimax_prompt(doc)
            try:r=render_packet({'shot_id':sid,'duration':doc['duration'],'prompt':prompt,'aspect_ratio':'16:9 (Widescreen)'},OUT/'shots',workflow='t2v_variable',poll=10,max_wait=1800)
            except Exception as exc:r={'shot_id':sid,'status':'failed','error':str(exc)}
            by[sid]=r;manifest.parent.mkdir(parents=True,exist_ok=True)
            manifest.write_text(json.dumps({'contract_dir':str(ROOT/'examples/script_first'),'workflow_profile':'t2v_variable','results':list(by.values())},ensure_ascii=False,indent=2),encoding='utf-8')
            print(sid,r.get('status'),r.get('task_id',''),r.get('error',''),flush=True)
    segs=[by.get(f'{sid_base}_T1',{}) for _,sid_base in SEGS]
    if all(x.get('status')=='success' for x in segs) and all(x.get('outputs') for x in segs):
        master=OUT/'coffee30_dir1_master.mp4'
        if not master.exists():
            files=[x['outputs'][0] for x in segs]
            master.parent.mkdir(parents=True,exist_ok=True)
            lst=OUT/'concat.txt';lst.write_text('\n'.join(f"file '{f}'" for f in files),encoding='utf-8')
            rc=subprocess.run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(master)]).returncode
            if rc!=0:
                rc=subprocess.run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(lst),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(master)]).returncode
            print('master_stitched' if rc==0 else 'master_failed',master,flush=True)
    return 1 if any(x.get('status')=='failed' for x in by.values()) else 0

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--takes',type=int,default=1);a=ap.parse_args();raise SystemExit(main(max(1,a.takes)))

