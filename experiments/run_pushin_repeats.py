"""Run three frozen repetitions of the single push-in MiniMax T2V recipe."""
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from shortfilm.prompt_contract import compile_minimax_prompt
from shortfilm.rh_adapter import render_packet
from shortfilm.cli.normalize_video import normalize
contract=json.loads((ROOT/'examples/director_contract/coffee_pushin_v2.json').read_text(encoding='utf-8'))
prompt=compile_minimax_prompt(contract); out=ROOT/'output/camera_pushin_v2/render'; manifest=out/'asset_manifest.json'; by={}
if manifest.exists():by={x['shot_id']:x for x in json.loads(manifest.read_text(encoding='utf-8')).get('results',[])}
for i in range(1,4):
 sid=f'PUSHIN_R{i}'
 if by.get(sid,{}).get('status')=='success':continue
 try:
  r=render_packet({'shot_id':sid,'duration':10,'prompt':prompt},out/'shots',workflow='t2v',poll=10,max_wait=1200)
  vertical=[]
  for raw in r.get('outputs',[]):
   src=Path(raw);dst=src.with_name(src.stem+'_vertical.mp4');normalize(src,dst,focus=.38);vertical.append(str(dst))
  r['raw_outputs']=r.get('outputs',[]);r['outputs']=vertical
 except Exception as exc:r={'shot_id':sid,'status':'failed','error':str(exc)}
 by[sid]=r;manifest.parent.mkdir(parents=True,exist_ok=True);manifest.write_text(json.dumps({'recipe':'single_pushin_v2','results':list(by.values())},ensure_ascii=False,indent=2),encoding='utf-8');print(sid,r.get('status'),r.get('task_id',''),r.get('error',''),flush=True)
raise SystemExit(1 if any(x.get('status')=='failed' for x in by.values()) else 0)
