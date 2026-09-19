# -*- coding: utf-8 -*-
import json, sys, subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from run_asr_gate import cer, norm_text
from indextts2_ab import W_LINES
OUT=HERE/'orpheus_test_output'/'indextts2_real_feishu'
def sec(p):
 r=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(p)],capture_output=True,text=True); return round(float(r.stdout.strip()),3)
from faster_whisper import WhisperModel
print('loading faster-whisper base (cpu/int8)...',flush=True)
model=WhisperModel('base',device='cpu',compute_type='int8')
rows=[]
for ln in W_LINES:
 p=OUT/(ln['id']+'.wav')
 if not p.exists(): continue
 segs,_=model.transcribe(str(p),language='zh',beam_size=5); hyp=''.join(s.text for s in segs)
 row={'id':ln['id'],'ref':ln['text'],'emotion':ln['emo'],'dur':sec(p),'asr':hyp,'cer':round(cer(ln['text'],hyp),3),'pass':cer(ln['text'],hyp)<=.15}
 rows.append(row); print(f"{ln['id']} CER={row['cer']:.3f} dur={row['dur']:.2f}s pass={row['pass']} asr={hyp}",flush=True)
cs=[x['cer'] for x in rows]; print(f'avg CER={sum(cs)/len(cs):.3f} pass={sum(x["pass"] for x in rows)}/{len(rows)}')
(OUT/'asr_results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print('saved',OUT/'asr_results.json')
