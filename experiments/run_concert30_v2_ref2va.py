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

G=[BASE/'refs_hcy_v2'/'G_ref06_direct_facecrop_PASS.jpg',BASE/'refs_hcy_v2'/'ref01_crop.jpg',BASE/'refs'/'ref05_dessert_tshirt.jpg',BASE/'refs'/'ref08_plush_toys_cardigan_v2.jpg',BASE/'refs'/'ref09_plush_toys_sweater.jpg']
# G pack v5 (2026-09-15 user: S2 regen bled the burgundy dress from ref01 full photo): swap full -> face crop.
# ref01_crop keeps the strongest geometry anchor without its clothing; ref03 (blur) & ref04 (weak anchor 0.275) stay out.
GEO_G=('Girl G exact face geometry from the references: a distinctly pointed chin with a V-shaped jawline '
       'tapering to a narrow chin, and proportionally small eyes with narrow lids. Never enlarge her eyes, '
       'never round or soften her chin, no beautification.')
COSTUME_G=('Costume rule: girl G wears a plain black casual top (matching her look throughout the film). '
           'Never copy clothing from the reference photos — no burgundy or red dress, no cardigan, '
           'no plush-toy sweater; the references define her FACE only.')
H=[BASE/'refs_hcy_v2'/'H1_front_natural_PASS.jpg',BASE/'refs_hcy_v2'/'H2_left_threequarter_PASS.jpg',BASE/'refs_hcy_v2'/'H4_singing_openmouth_PASS.jpg',BASE/'refs_hcy_v2'/'H3_right_threequarter_LOW_WEIGHT.jpg',BASE/'refs_hcy_v2'/'H5_fullbody_look_PASS.jpg']
# v3: singer face-crop anchor FIRST (transpose of validated girl recipe), SameFace 0.5
HF=[BASE/'refs_hcy_v2'/'H1_facecrop.jpg',BASE/'refs_hcy_v2'/'H4_singing_openmouth_PASS.jpg',BASE/'refs_hcy_v2'/'H1_front_natural_PASS.jpg',BASE/'refs_hcy_v2'/'H5_fullbody_look_PASS.jpg']
SEGS='segments_v3.json' if (BASE/'segments_v3.json').exists() else 'segments_v2.json'

def load(): return json.loads((BASE/SEGS).read_text(encoding='utf-8'))
def plan(): return json.loads((BASE/'production_plan_v2.json').read_text(encoding='utf-8'))

def refs_for(seg):
    mode=seg.get('generation_mode','')
    if mode=='real_cut': return []
    if mode=='girl_plate_plus_real_insert': return G
    if mode=='hua_plate': return HF
    if mode=='two_person_plate': return G+HF
    return G+H

def prompt(seg, refs):
    mode=seg.get('generation_mode','')
    rel=[round(a-seg['time'][0],2) for a in seg['anchors']]
    if mode=='hua_plate':
        defs=('<Picture 1> supplies singer H exact face geometry (frontal anchor crop); '
              '<Picture 2> supplies his open-mouth singing expression; '
              '<Picture 3> supplies his hair and frontal look; '
              '<Picture 4> supplies his full-body stage costume. '
              'All four pictures define the same real singer H; preserve his exact facial geometry, not a lookalike.')
        return defs+f"""
summary:
[reference generation] {seg['id']} singer plate for a loud, packed 2024 Mars Concert. One single continuous scene, no montage: {seg['plate']}.
retention_analysis:
Only one identity appears: singer H, the continuous main subject of every frame from start to end. His face is clearly visible toward camera within the first second and again in the last second; between them he stays mid-performance. Crowd faces remain unresolved smears in darkness. H keeps his platinum-blonde shaggy hair, pink sequin-embroidered stage costume and red wireless microphone in every frame.
detailed_description:
Loud, kinetic live-concert realism: darkness beyond the stage light, glow-stick ocean, sweeping beams, haze, LED glare. Every movement hits these relative audio anchors: {rel}. Hard mandatory attributes in EVERY frame: platinum-blonde shaggy hair, pink sequin stage costume, red wireless microphone in hand, visibly singing with mouth open. Strictly forbidden: any second prominent man, backup dancers, resolved audience faces, quiet pauses, stillness, walking off stage, instrument playing.
overall_soundscape: arena screaming, live vocals from the stage; no quiet gap.
non_diegetic_music: none; final edit uses the approved genuine live master window."""
    if mode=='two_person_plate':
        defs=[]
        for i,p in enumerate(refs,1):
            role='girl G' if p in G else 'singer H'
            defs.append(f'<Picture {i}> supplies the exact face and look of {role};' if i in (1,len(G)+1) else f'<Picture {i}> is another view of {role};')
        defs='\n'.join(defs)+' Girl G and singer H are two distinct real identities; preserve each one\'s exact facial geometry, never blend, swap, average or morph their faces.'
        return defs+f"""
summary:
[reference generation] {seg['id']} in a loud, packed 2024 Mars Concert. One single continuous scene, no montage: {seg['plate']}.
retention_analysis:
Both identities appear and stay themselves in every frame: girl G with her thin round glasses and long dark hair, singer H with platinum-blonde shaggy hair, pink sequin costume and red microphone. {GEO_G} Their faces are both clearly visible toward camera within the first second and again in the last second. Crowd faces remain unresolved smears in darkness.
detailed_description:
Loud, kinetic live-concert realism: darkness around the action, glow-stick ocean, sweeping beams, haze, LED glare. Every movement hits these relative audio anchors: {rel}. Both faces stay in frame together for most of the clip; no coverage where either face vanishes. {GEO_G} {COSTUME_G} Hands anatomically correct; the bouquet stays intact and held high. Strictly forbidden: face blending or swapping between G and H, any third prominent person, resolved audience faces, quiet pauses.
overall_soundscape: arena screaming, live vocals, band and drums; no quiet gap.
non_diegetic_music: none; final edit uses the approved genuine live master window."""
    if mode=='girl_plate_plus_real_insert':
        defs='\n'.join(f'<Picture {i}> defines the same real girl G in different daily contexts; preserve her exact facial geometry, glasses and proportions, not a lookalike.' for i in range(1,len(refs)+1))
        return defs+f"""
summary:
[reference generation] {seg['id']} girl plate for a loud, packed 2024 Mars Concert. One single continuous scene, no montage: {seg['plate']}.
retention_analysis:
Only one identity appears: girl G, and she is the continuous main subject of every frame from start to end — never a background figure. Her face is clearly visible toward camera within the first second and again in the last second; between them she may be mid-action but never vanishes. {GEO_G} No male singer is generated in sharp focus; any stage figure stays tiny, backlit and unresolved. Crowd faces remain unresolved smears. G keeps her thin round glasses and exact facial geometry from the references at every visible moment.
detailed_description:
Fast, noisy, kinetic live-concert realism: darkness beyond the follow spot, red glow-stick ocean flickering in the dark, sweeping beams, haze, distant stage glare, motion blur on the dark crowd around her. Every movement hits these relative audio anchors: {rel}. Hard mandatory attributes in EVERY frame: girl G wears her thin round glasses and has her long dark hair exactly as in the references; {COSTUME_G} {GEO_G} {seg.get('action_mandate','she moves at an energetic fast pace from the first frame to the last — never calm walking, never standing still')}; bouquet held firmly with anatomically correct hands. Strictly forbidden: selfies, group photos, phones facing the viewer, vlogging poses, quiet pauses, calm walking, standing and smiling at the camera, any second prominent woman, empty corridors or backstage tunnels — she is always inside a dense dark crowd or lit by the follow spot within the arena.
overall_soundscape: arena screaming, live drums and vocals bleeding from the stage; no quiet gap.
non_diegetic_music: none; final edit uses the approved genuine live master window."""
    defs=[]
    for i,p in enumerate(refs,1):
        role='the same real girl G' if p in G else 'the same real Hua Chenyu H'
        defs.append(f'<Picture {i}> defines {role}; preserve exact facial geometry, not a lookalike.')
    return '\n'.join(defs)+f"""
summary:
[reference generation] {seg['id']} in a loud, packed 2024 Mars Concert. {seg['plate'] or seg['visual']}
retention_analysis:
G and H are two distinct real identities. Never blend, swap, average or morph their faces. Girl G keeps thin round glasses. The singer keeps the 2024 gold-hair stage look with red microphone and must stay visibly singing; his face will be role-isolated repaired or replaced by genuine footage in post — keep his blocking simple and his face angles few. Crowd faces remain unresolved.
detailed_description:
Fast, noisy, kinetic live-concert realism. Every cut and movement hits these relative audio anchors: {rel}. Huge LED arrays, moving beams, haze, glow-stick ocean, jumping crowd and handheld stage-camera energy. No calm walking, no quiet pause, no ceremonial slowdown. End with at least one clear identity-validation face angle when physically plausible.
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
    sameface=0.5 if seg.get('generation_mode') in ('girl_plate_plus_real_insert','hua_plate','two_person_plate') else 0.35
    fmt['158']={'class_type':'LoraLoaderModelOnly','inputs':{'lora_name':'SameFace_Fix.safetensors','strength_model':sameface,'model':['127',0]}}
    fmt['159']={'class_type':'LoraLoaderModelOnly','inputs':{'lora_name':'minimax_h3_turbo_6step_ema.safetensors','strength_model':1.0,'model':['158',0]}}
    fmt['141']['inputs']['model']=['159',0]
    for nid in ('124','126'):
        if fmt[nid]['inputs'].get('model')==['127',0]: fmt[nid]['inputs']['model']=['159',0]
    fmt['124']['inputs']['steps']=6
    return refs,fmt

def preflight():
    errors=[]; rows=[]
    for seg in load()['segments']:
        mode=seg.get('generation_mode','')
        if mode=='real_cut':
            rows.append({'id':seg['id'],'mode':mode,'refs':0,'note':'genuine footage cut, no generation'})
            continue
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
    if seg.get('generation_mode')=='real_cut': raise SystemExit(f'{sid} is a real-footage cut; use ffmpeg, no paid run')
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
