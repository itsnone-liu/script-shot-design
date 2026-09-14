"""Scan a video for large, sharp face-reference candidates using OpenCV YuNet."""
from __future__ import annotations
import argparse, csv
from pathlib import Path
import cv2

MODEL = Path(r"D:\qjcNetDiskDownload\deepseek-harness\project\820\data\models\yunet.onnx")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--step", type=float, default=0.5)
    ap.add_argument("--top", type=int, default=30)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(args.video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frames / fps
    det = cv2.FaceDetectorYN.create(str(MODEL), "", (320, 320), score_threshold=0.65)
    found = []
    stride = max(1, round(fps * args.step))
    frame_index = 0
    while True:
        ok, img = cap.read()
        if not ok:
            break
        if frame_index % stride:
            frame_index += 1
            continue
        t = frame_index / fps
        h, w = img.shape[:2]
        detect_scale = min(1.0, 960.0 / w)
        detect_img = cv2.resize(img, (round(w * detect_scale), round(h * detect_scale))) if detect_scale < 1 else img
        det.setInputSize((detect_img.shape[1], detect_img.shape[0]))
        _, faces = det.detect(detect_img)
        if faces is not None:
            for f in faces:
                x, y, fw, fh = [int(v / detect_scale) for v in f[:4]]
                conf = float(f[-1])
                x0, y0 = max(0, x), max(0, y)
                x1, y1 = min(w, x + fw), min(h, y + fh)
                crop = img[y0:y1, x0:x1]
                if crop.size == 0: continue
                sharp = float(cv2.Laplacian(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())
                area_ratio = (fw * fh) / (w * h)
                score = area_ratio * conf * min(sharp / 100.0, 3.0)
                found.append((score, t, x0, y0, x1-x0, y1-y0, conf, sharp, img.copy(), crop.copy()))
        frame_index += 1
    cap.release()
    found.sort(key=lambda z: z[0], reverse=True)
    chosen = []
    for row in found:
        if all(abs(row[1] - x[1]) >= 1.5 for x in chosen):
            chosen.append(row)
        if len(chosen) >= args.top: break
    with (args.out / "candidates.csv").open("w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f); wr.writerow(["rank","time","score","x","y","w","h","confidence","sharpness"])
        for rank, row in enumerate(chosen, 1):
            score,t,x,y,fw,fh,conf,sharp,img,crop=row
            name=f"{rank:02d}_{t:07.2f}s"
            cv2.rectangle(img,(x,y),(x+fw,y+fh),(0,255,0),3)
            cv2.imwrite(str(args.out/f"{name}_frame.jpg"),img)
            cv2.imwrite(str(args.out/f"{name}_face.jpg"),crop)
            wr.writerow([rank,f"{t:.2f}",f"{score:.6f}",x,y,fw,fh,f"{conf:.4f}",f"{sharp:.2f}"])
    print(f"duration={duration:.3f}s detections={len(found)} selected={len(chosen)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
