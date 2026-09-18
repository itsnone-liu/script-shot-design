"""C2《再睡五分钟》身份资产包预处理 —— 2026-09-16。

步骤 0（本脚本）：原图 → P1 脸裁切锚 + 检测框元数据 + 基准嵌入。
转正组生成（Ref2VA/RH）与门禁验收见后续步骤；本脚本只做本地确定性处理。

用法：
    python experiments/couple30_identity_prep.py
产物（examples/couple30_v1/identity/）：
    ref_original.jpg   原图（门禁基准，不动）
    face_crop.jpg      P1 脸部裁切锚（含发际/下巴余量的方形区域）
    face_box.json      检测框+关键点+裁切框（供 ReActor/对齐用）
    ref_embedding.npy  原图基准嵌入（SFace，转正组比对基准）
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "820"))
from experiments.metrics import FaceComparator  # noqa: E402

IDENT = ROOT / "examples" / "couple30_v1" / "identity"


def main() -> None:
    src = IDENT / "ref_original.jpg"
    assert src.exists(), f"missing {src}"
    cmp_ = FaceComparator()
    img = cv2.imread(str(src))
    h, w = img.shape[:2]

    det = cmp_.det
    det.setInputSize((w, h))
    _, faces = det.detect(img)
    assert faces is not None and len(faces), "no face detected in ref_original"
    areas = faces[:, 2] * faces[:, 3]
    i = int(np.argmax(areas))
    f = faces[i]
    x, y, fw, fh = (float(v) for v in f[:4])
    score = float(f[14]) if len(f) > 14 else None
    # 关键点 5 个 (x,y)：右眼/左眼/鼻尖/右嘴角/左嘴角 = f[4:14]
    kps = [float(v) for v in f[4:14]]
    print(f"face box=({x:.0f},{y:.0f},{fw:.0f}x{fh:.0f}) score={score:.3f}")

    # P1 裁切锚：以脸框为中心，宽=2.2*fw，高=2.4*fh（发际+下巴余量），方形化
    cw, ch = fw * 2.2, fh * 2.4
    side = max(cw, ch)
    cx, cy = x + fw / 2, y + fh / 2
    # 眼睛在框上部 1/3 处：把中心往上挪一点，多留下巴以下（锁骨方向）内容
    cy = cy + fh * 0.18
    x0, y0 = int(cx - side / 2), int(cy - side / 2)
    x1, y1 = x0 + int(side), y0 + int(side)
    # 裁切越界则平移夹回（不 pad，避免黑边）
    x0, y0 = max(0, min(x0, w - int(side) if w > side else 0)), max(0, min(y0, h - int(side) if h > side else 0))
    x1, y1 = min(w, x0 + int(side)), min(h, y0 + int(side))
    crop = img[y0:y1, x0:x1]
    out = IDENT / "face_crop.jpg"
    cv2.imwrite(str(out), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print(f"face_crop.jpg {crop.shape[1]}x{crop.shape[0]}")

    # 基准嵌入（用 alignCrop 的标准 112x112，与后续比对同管线）
    aligned = cmp_.largest_face(img)
    emb = cmp_.embed(aligned)
    np.save(IDENT / "ref_embedding.npy", emb)

    import json
    (IDENT / "face_box.json").write_text(json.dumps({
        "source": str(src),
        "image_size": [w, h],
        "face_box_xywh": [x, y, fw, fh],
        "detect_score": score,
        "keypoints": kps,
        "crop_xyxy": [x0, y0, x1, y1],
        "crop_policy": "center=face_center+0.18*fh_down, side=max(2.2*fw, 2.4*fh)",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # 自检：裁切锚上应仍能检出同一张脸（管线自洽性）
    r = cmp_.score(src, out)
    print(f"self-check ref vs face_crop: cos={r.get('cosine')} same={r.get('same_person')}")


if __name__ == "__main__":
    main()
