"""Rank extracted images by largest YuNet face area, confidence and sharpness."""
import argparse, csv, shutil
from pathlib import Path
import cv2

MODEL = Path(r"D:\qjcNetDiskDownload\deepseek-harness\project\820\data\models\yunet.onnx")
ap=argparse.ArgumentParser(); ap.add_argument("source",type=Path); ap.add_argument("out",type=Path); ap.add_argument("--top",type=int,default=30); a=ap.parse_args()
a.out.mkdir(parents=True,exist_ok=True)
det=cv2.FaceDetectorYN.create(str(MODEL),"",(320,320),score_threshold=.65)
rows=[]
for p in sorted(a.source.glob("*.jpg")):
    img=cv2.imread(str(p)); h,w=img.shape[:2]; det.setInputSize((w,h)); _,faces=det.detect(img)
    if faces is None: continue
    for f in faces:
        x,y,fw,fh=[int(v) for v in f[:4]]; conf=float(f[-1]); crop=img[max(0,y):min(h,y+fh),max(0,x):min(w,x+fw)]
        if not crop.size: continue
        sharp=float(cv2.Laplacian(cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY),cv2.CV_64F).var()); area=fw*fh/(w*h); score=area*conf*min(sharp/100,3)
        rows.append((score,p,x,y,fw,fh,conf,sharp,crop))
rows.sort(reverse=True,key=lambda z:z[0]); chosen=[]
for r in rows:
    n=int(r[1].stem.split('_')[-1]);
    if all(abs(n-int(q[1].stem.split('_')[-1]))>=2 for q in chosen): chosen.append(r)
    if len(chosen)>=a.top: break
with (a.out/'candidates.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['rank','frame_file','approx_second','score','face_w','face_h','confidence','sharpness'])
    for i,r in enumerate(chosen,1):
        score,p,x,y,fw,fh,conf,sharp,crop=r; sec=int(p.stem.split('_')[-1])-1; stem=f'{i:02d}_{sec:04d}s'; shutil.copy2(p,a.out/f'{stem}_frame.jpg'); cv2.imwrite(str(a.out/f'{stem}_face.jpg'),crop); w.writerow([i,p.name,sec,f'{score:.6f}',fw,fh,f'{conf:.4f}',f'{sharp:.2f}'])
print(f'images={len(list(a.source.glob("*.jpg")))} detections={len(rows)} selected={len(chosen)}')
