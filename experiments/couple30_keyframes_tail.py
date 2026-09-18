# -*- coding: utf-8 -*-
"""C2 A_LAST / C_LAST 关键帧补帧：以已批准稳定帧做 Klein 小步编辑。"""
from __future__ import annotations
import io, json, shutil, sys
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
ROOT=Path(__file__).resolve().parents[1]
P820=ROOT.parent/'820'
KF=ROOT/'examples/couple30_v1/keyframes'
sys.path.insert(0,str(P820)); sys.path.insert(0,str(P820/'experiments'))
from experiments import rh_task

WEBAPP='2075052610570244098'
BASE=("图一是已经确认通过的关键帧，图二是同一女性身份参考。只做指定的小改动，"
      "严格保持两个人的身份、脸型、发型、服装、床铺、构图、体位、光线和背景完全不变，"
      "不要重新设计人物，不要改变镜头，不要增加人物，不要改变脸型。")
TASKS={
 'KF_A_LAST': (KF/'KF_A1.png',
   BASE+"女方说完话后带着胜利的笑意，右手轻轻捏住男方鼻尖；男方仍闭眼装睡，"
   "嘴角忍笑。动作幅度很小，保持女方趴在男方身上的原有姿势。"),
 'KF_C_LAST': (KF/'KF_B_LAST.png',
   BASE+"男方俯身靠近，食指轻轻触碰女方鼻尖；两人温柔对视并微笑，"
   "鼻尖接近但不接吻、不张嘴亲吻，保持男上女下的原有姿势和完整衣物。")
}

def run(name, src, prompt):
    key=rh_task.load_api_key()
    u1=rh_task.upload_file(key,src); u2=rh_task.upload_file(key,src)
    nodes=[{'nodeId':'597','fieldName':'image','fieldValue':u1},
           {'nodeId':'598','fieldName':'image','fieldValue':u2},
           {'nodeId':'500','fieldName':'text','fieldValue':prompt}]
    tid=rh_task.run_webapp(key,WEBAPP,nodes)
    print(name,tid,flush=True)
    out=rh_task.wait_task(key,tid,poll=8,max_wait=900,
      on_progress=lambda t,s: print(name,s,flush=True))
    for url in rh_task.collect_file_urls(out):
        if url.lower().split('?')[0].endswith(('.png','.jpg','.jpeg','.webp')):
            dest=KF/f'{name}.png'; rh_task.download(url,dest); print('saved',dest); return
    raise RuntimeError('no image output')

for name,(src,prompt) in TASKS.items(): run(name,src,prompt)
