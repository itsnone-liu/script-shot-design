# -*- coding: utf-8 -*-
"""couple30_keyframe_index_calibrate.py — ReActor 双人运行时脸序号校准。

不使用 YuNet 面积/位置推断 ReActor index；对每个候选 index 实跑，逐脸打分并保留两版。
"""
from __future__ import annotations
import io, json, sys
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
ROOT=Path(__file__).resolve().parents[1]; P820=ROOT.parent/'820'
sys.path.insert(0,str(P820)); sys.path.insert(0,str(P820/'experiments'))
import cv2, numpy as np
import swap_face as sf
from experiments.metrics import FaceComparator
from experiments import rh_task
KF=ROOT/'examples/couple30_v1/keyframes'; REF=ROOT/'examples/couple30_v1/identity/refs_extra/ref03.jpg'
fc=FaceComparator(); e=fc.embed(fc.largest_face(cv2.imread(str(REF))))

def detect(path):
 img=cv2.imread(str(path)); h,w=img.shape[:2]; fc.det.setInputSize((w,h)); _,faces=fc.det.detect(img)
 arr=[]
 if faces is not None:
  for i,f in enumerate(faces):
   al=fc.rec.alignCrop(img,f); arr.append({'det_i':i,'x':round(float(f[0])),'y':round(float(f[1])),'w':round(float(f[2])),'h':round(float(f[3])),'score':round(float(f[14]),3),'cos':round(float(fc.cosine(fc.embed(al),e)),4)})
 return sorted(arr,key=lambda z:-z['w']*z['h'])

def run(name, plate, idx):
 api=json.loads((P820/'data/api_format/_reactor_single_c30.json').read_text(encoding='utf-8'))
 api['15']['inputs']['input_faces_index']=str(idx)
 api['15']['inputs']['face_restore_visibility']=0.25
 wf=f'_reactor_cal_{name}_{idx}'
 (P820/f'data/api_format/{wf}.json').write_text(json.dumps(api,ensure_ascii=False),encoding='utf-8')
 sf.WORKFLOWS[wf]={'workflow_id':wf,'webapp_id':'','ref':'2.image','target':'1.image','note':f'index calibration {idx}'}
 meta=sf.run_swap(wf,plate,REF,tag=f'c30_cal_{name}_{idx}',max_wait=600)
 files=[Path(x) for x in meta.get('files',[]) if Path(x).suffix.lower()=='.png']
 if not files: raise RuntimeError('no output')
 out=KF/f'{name}_idx{idx}.png'; out.write_bytes(files[0].read_bytes())
 return {'name':name,'input_index':idx,'output':str(out),'faces':detect(out)}

print('PLATE DETECTIONS')
for name in ('A1','B_LAST'):
 plate=KF/f'KF_{name}_plate.png'; print(name,detect(plate))
rows=[]
for name in ('A1','B_LAST'):
 plate=KF/f'KF_{name}_plate.png'
 for idx in (0,1):
  try:
   r=run(name,plate,idx); rows.append(r); print(json.dumps(r,ensure_ascii=False))
  except Exception as ex: print(name,idx,'FAILED',repr(ex))
(KF/'index_calibration.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
