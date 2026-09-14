# -*- coding: utf-8 -*-
"""Build/preflight concert30 v2 H3 Ref2VA jobs. Paid run stays locked by production_plan_v2.json."""
from __future__ import annotations
import argparse, json, sys, time, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / '820'))
from experiments import rh_task

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'examples'/'concert30_hcy_flowers'
P820=ROOT.parent/'820'
TEMPLATE=P820/'_h3ref2va_apifmt.json'
CID='2093518439926218753'

G=[BASE/'refs'/'ref05_dessert_tshirt.jpg',BASE/'refs_hcy_v2'/'G_ref06_direct_facecrop_PASS.jpg',BASE/'refs'/'ref03_stadium_selfie.jpg',BASE/'refs'/'ref04_theater_hoodie.jpg']
H=[BASE/'refs_hcy_v2'/'H1_front_natural_PASS.jpg',BASE/'refs_hcy_v2'/'H2_left_threequarter_PASS.jpg',BASE/'refs_hcy_v2'/'H4_singing_openmouth_PASS.jpg',BASE/'refs_hcy_v2'/'H3_right_threequarter_LOW_WEIGHT.jpg',BASE/'refs_hcy_v2'/'H5_fullbody_look_PASS.jpg']

def load(): return json.loads((BASE/'segments_v2.json').read_text(encoding='utf-8'))
def plan(): return json.loads((BASE/'production_plan_v2.json').read_text(encoding='utf-8'))

def refs_for(seg):
    roles=seg['identity_roles']
    if roles==['hua_chenyu']: return H
    return G+H

def prompt(seg, refs):
    defs=[]
    for i,p in enumerate(refs,1):
        role='the same real girl G' if p in G else 'the same real Hua Chenyu H'
        defs.append(f'<Picture {i}> defines {role}; preserve exact facial geometry, not a lookalike.')
    return '\n'.join(defs)+f"""
summary:
[reference generation] {seg['id']} in a loud, packed 2024 Mars Concert. {seg['visual']}
retention_analysis:
G and H are two distinct real identities. Never blend, swap, average or morph their faces. Girl G keeps thin round glasses. Hua Chenyu H keeps the selected 2024 gold-hair stage look and red microphone. Crowd faces remain unresolved.
detailed_description:
Fast, noisy, kinetic live-concert realism. Every cut and movement hits these relative audio anchors: {seg['anchors']}. Hua Chenyu is visibly singing whenever on screen. Huge LED arrays, moving beams, haze, glow-stick ocean, jumping crowd and handheld stage-camera energy. No calm walking, no quiet pause, no ceremonial slowdown. End with at least one clear identity-validation face angle when physically plausible.
overall_soundscape: genuine arena vocal performance, live band, drums, crowd singing and screaming; no quiet gap.
non_diegetic_music: none; final edit uses the approved genuine live master window."""

def build(seg):
    refs=refs_for(seg); fmt=json.loads(TEMPLATE.read_text(encoding='utf-8'))
    # Paths are placeholders in preflight; paid runner uploads and substitutes openapi paths.
    for i,p in enumerate(refs):
        nid='137' if i==0 else str(199+i)
        if i==0: fmt['137']['inputs']['image']=str(p)
        else: fmt[nid]={'class_type':'LoadImage','inputs':{'image':str(p)}}
        fmt['136']['inputs'][f'ref_images.ref_image_{i}']=[nid,0]
    ri=fmt['136']['inputs']; ri['ref_image_size']='max'; ri['width']=1344; ri['height']=768
    dur=round(seg['time'][1]-seg['time'][0],2); fmt['132']['inputs']['value']=dur; fmt['138']['inputs']['value']=prompt(seg,refs)
    fmt['127']['inputs']['unet_name']='minimax_h3_ref2va_pruned_int8_convrot.safetensors'
    fmt['158']={'class_type':'LoraLoaderModelOnly','inputs':{'lora_name':'SameFace_Fix.safetensors','strength_model':0.35,'model':['127',0]}}
    fmt['159']={'class_type':'LoraLoaderModelOnly','inputs':{'lora_name':'minimax_h3_turbo_6step_ema.safetensors','strength_model':1.0,'model':['158',0]}}
    fmt['141']['inputs']['model']=['159',0]
    for nid in ('124','126'):
        if fmt[nid]['inputs'].get('model')==['127',0]: fmt[nid]['inputs']['model']=['159',0]
    fmt['124']['inputs']['steps']=6
    return refs,fmt

def preflight():
    errors=[]; rows=[]
    for seg in load()['segments']:
        refs,fmt=build(seg); dur=fmt['132']['inputs']['value']; text=fmt['138']['inputs']['value']
        miss=[str(p) for p in refs if not p.exists()]
        if miss: errors.append(f"{seg['id']} missing refs: {miss}")
        if not 4<=dur<=15: errors.append(f"{seg['id']} duration {dur} outside 4-15")
        if len(refs)>9: errors.append(f"{seg['id']} has {len(refs)} refs > 9")
        if fmt.get('138',{}).get('class_type') not in ('PrimitiveStringMultiline','PrimitiveNode'):
            errors.append(f"{seg['id']} prompt node 138 was overwritten")
        links=[fmt['136']['inputs'].get(f'ref_images.ref_image_{i}') for i in range(len(refs))]
        if len({x[0] for x in links if x}) != len(refs): errors.append(f"{seg['id']} duplicate reference node ids")
        rows.append({'id':seg['id'],'duration':dur,'refs':len(refs),'prompt_chars':len(text),'missing':miss})
    print(json.dumps({'workflow_id':CID,'paid_generation_locked':plan().get('paid_generation_locked'),'segments':rows,'errors':errors},ensure_ascii=False,indent=2))
    return 1 if errors else 0

def run_one(sid):
    if plan().get('paid_generation_locked'): raise SystemExit('REFUSED: v2 paid_generation_locked')
    seg=next((x for x in load()['segments'] if x['id']==sid),None)
    if not seg: raise SystemExit(f'unknown segment {sid}')
    refs,fmt=build(seg); key=rh_task.load_api_key()
    if not key: raise SystemExit('missing RunningHub API key')
    for i,p in enumerate(refs):
        nid='137' if i==0 else str(199+i)
        uploaded=rh_task.upload_file(key,p)
        fmt[nid]['inputs']['image']=uploaded
        print(f'[{sid}] upload Picture {i+1} {p.name} -> {uploaded}',flush=True)
    tid=rh_task.run_workflow_json(key,fmt,sandbox_id=CID)
    print(f'[{sid}] task {tid}',flush=True)
    out=ROOT/'output'/'concert30_hcy_flowers_v2'/'shots'; out.mkdir(parents=True,exist_ok=True)
    result=rh_task.wait_task(key,tid,poll=30,max_wait=1800,on_progress=lambda t,s:print(f'[{sid}] {s}',flush=True))
    urls=rh_task.collect_file_urls(result)
    records=[]
    for n,u in enumerate(urls):
        ext='.zip' if '.zip' in u.lower() else '.mp4'
        target=out/f'{sid}_{n:02d}{ext}'; rh_task.download(u,target); records.append(str(target))
        if ext=='.zip':
            with zipfile.ZipFile(target) as z: z.extractall(out/f'{sid}_unzipped')
    state={'segment':sid,'task_id':tid,'status':'SUCCESS','outputs':records}
    (out/f'{sid}_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(state,ensure_ascii=False,indent=2)); return 0

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--preflight',action='store_true'); ap.add_argument('--run',metavar='S1'); a=ap.parse_args()
    return run_one(a.run) if a.run else preflight()
if __name__=='__main__': raise SystemExit(main())
