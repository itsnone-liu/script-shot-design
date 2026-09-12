"""Run the frozen camera-prompt A/B serially on the 10s T2V card."""
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from shortfilm.rh_adapter import render_packet
from shortfilm.cli.normalize_video import normalize

project=json.loads((ROOT/'examples/director_contract/experiment_project.json').read_text(encoding='utf-8'))
out=ROOT/'output/camera_prompt_ab_v1/render10'
manifest=out/'asset_manifest.json'; results=[]
if manifest.exists(): results=json.loads(manifest.read_text(encoding='utf-8')).get('results',[])
by_id={x.get('shot_id'):x for x in results}
for shot in project['shots']:
    sid=shot['shot_id']
    if by_id.get(sid,{}).get('status')=='success': continue
    packet={'shot_id':sid,'duration':10,'prompt':shot['generation_prompt']}
    try:
        result=render_packet(packet,out/'shots',workflow='t2v',poll=10,max_wait=1200)
        vertical=[]
        for raw in result.get('outputs',[]):
            src=Path(raw); dst=src.with_name(src.stem+'_vertical.mp4'); normalize(src,dst,focus=.38); vertical.append(str(dst))
        result['raw_outputs']=result.get('outputs',[]); result['outputs']=vertical
    except Exception as exc: result={'shot_id':sid,'status':'failed','error':str(exc)}
    by_id[sid]=result
    manifest.parent.mkdir(parents=True,exist_ok=True)
    manifest.write_text(json.dumps({'workflow':'t2v','duration':10,'results':list(by_id.values())},ensure_ascii=False,indent=2),encoding='utf-8')
    print(sid,result.get('status'),result.get('task_id',''),result.get('error',''),flush=True)
raise SystemExit(1 if any(x.get('status')=='failed' for x in by_id.values()) else 0)
