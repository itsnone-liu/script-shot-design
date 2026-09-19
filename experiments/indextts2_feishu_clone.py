# -*- coding: utf-8 -*-
"""Clone the female voice from the supplied Feishu recording with RH IndexTTS2."""
from __future__ import annotations
import argparse, json, subprocess, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE)); sys.path.insert(0,r'D:\qjcNetDiskDownload\deepseek-harness\project\820')
from experiments import rh_task
from indextts2_ab import INDEXTTS_APP, W_LINES
SRC=HERE/'飞书20260919-203153.mp4'
OUT=HERE/'orpheus_test_output'/'indextts2_real_feishu'; OUT.mkdir(parents=True,exist_ok=True)
REF=OUT/'ref_feishu_w.wav'
def sec(p):
 r=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(p)],capture_output=True,text=True); return round(float(r.stdout.strip()),3)
def make_ref():
 if not REF.exists():
  subprocess.run(['ffmpeg','-y','-v','error','-i',str(SRC),'-vn','-ac','1','-ar','24000','-af','silenceremove=start_periods=1:start_duration=0.15:start_threshold=-42dB:stop_periods=1:stop_duration=0.35:stop_threshold=-42dB',str(REF)],check=True)
 print('ref',REF,sec(REF),'s'); return REF
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--only'); ap.add_argument('--asr-only',action='store_true'); args=ap.parse_args()
 lines=[x for x in W_LINES if not args.only or x['id']==args.only]
 if args.only and not lines: raise SystemExit('unknown line '+args.only)
 if not args.asr_only:
  key=rh_task.load_api_key();
  if not key: raise SystemExit('RH api key missing')
  u=rh_task.upload_file(key,make_ref()); print('uploaded',u,flush=True)
  for ln in lines:
   dest=OUT/(ln['id']+'.wav')
   if dest.exists(): print('exists',dest); continue
   nodes=[{'nodeId':'11','fieldName':'prompt','fieldValue':ln['emo']},{'nodeId':'4','fieldName':'prompt','fieldValue':ln['text']},{'nodeId':'10','fieldName':'audio','fieldValue':u}]
   t=time.time(); tid=rh_task.run_webapp(key,INDEXTTS_APP,nodes); print(ln['id'],tid,flush=True)
   result=rh_task.wait_task(key,tid,poll=8,max_wait=600); urls=rh_task.collect_file_urls(result)
   if not urls: print('NO OUTPUT',ln['id']); continue
   mp4=[x for x in urls if '.wav' in x.lower() or '.mp3' in x.lower() or '.zip' not in x.lower()]; rh_task.download(mp4[0] if mp4 else urls[0],dest); print('done',dest,sec(dest),time.time()-t,flush=True)
 if args.asr_only: print('outputs',[(p.name,sec(p)) for p in OUT.glob('L*.wav')])
if __name__=='__main__': main()
