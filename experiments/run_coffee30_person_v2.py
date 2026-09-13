"""Render segA v2 only and stitch with the already-rendered v1 segment B.
The v2 revision targets the pacing complaint: five unequal shots, one long
take, light as the traveling motif. Segment B (milk/hero) was approved and
stays byte-identical from coffee30_person_v1.
"""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from shortfilm.prompt_contract import compile_minimax_prompt,validate_director_contract
from shortfilm.rh_adapter import render_packet

CONTRACT_A=ROOT/'examples/script_first/coffee30_person_segA_v2.json'
B_FILE=ROOT/'output/script_first/coffee30_person_v1/shots/COFFEE30B_T1_00.mp4'
OUT=ROOT/'output/script_first/coffee30_person_v2'

def main()->int:
    doc=json.loads(CONTRACT_A.read_text(encoding='utf-8'))
    r=doc.get('user_script_review') or {}
    if r.get('status')!='approved' or not r.get('reviewed_by'):
        print('REFUSED - direct user approval required');return 2
    errs=validate_director_contract(doc)
    if errs:print('CONTRACT INVALID:',*errs,sep='\n- ');return 3
    if not B_FILE.exists():print('missing segment B:',B_FILE);return 4
    manifest=OUT/'asset_manifest.json';by={}
    if manifest.exists():by={x['shot_id']:x for x in json.loads(manifest.read_text(encoding='utf-8')).get('results',[])}
    sid='COFFEE30A2_T1'
    if by.get(sid,{}).get('status')!='success':
        prompt=compile_minimax_prompt(doc)
        try:res=render_packet({'shot_id':sid,'duration':doc['duration'],'prompt':prompt,'aspect_ratio':'16:9 (Widescreen)'},OUT/'shots',workflow='t2v_variable',poll=10,max_wait=1800)
        except Exception as exc:res={'shot_id':sid,'status':'failed','error':str(exc)}
        by[sid]=res;manifest.parent.mkdir(parents=True,exist_ok=True)
        manifest.write_text(json.dumps({'contract':str(CONTRACT_A),'reused_segment_b':str(B_FILE),'results':list(by.values())},ensure_ascii=False,indent=2),encoding='utf-8')
        print(sid,res.get('status'),res.get('task_id',''),res.get('error',''),flush=True)
    if by.get(sid,{}).get('status')=='success' and by[sid].get('outputs'):
        master=OUT/'coffee30_person_v2_master.mp4'
        if not master.exists():
            a=by[sid]['outputs'][0];lst=OUT/'concat.txt'
            lst.parent.mkdir(parents=True,exist_ok=True)
            lst.write_text('\n'.join(f"file '{p}'" for p in (a,str(B_FILE))),encoding='utf-8')
            rc=subprocess.run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(master)]).returncode
            if rc!=0:rc=subprocess.run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(lst),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(master)]).returncode
            print('master_stitched' if rc==0 else 'master_failed',master,flush=True)
    return 0 if by.get(sid,{}).get('status')=='success' else 1

if __name__=='__main__':raise SystemExit(main())
