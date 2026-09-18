# -*- coding: utf-8 -*-
"""C2 关键帧生产 —— 2026-09-17（转正组 v6 已验收，进入视频阶段）。

关键帧集（审批门）：
  KF_A1    女趴男身面对面（A 容器首帧，openpose 层叠骨架）
  KF_A_LAST A 容器尾帧（同姿态表情推进，由 KF_A1 图生图微调，本轮先出基础版）
  KF_B_LAST 翻转后男上女下（B/C 容器姿态锚）
  KF_M      男主锚（纯文本 Z-Image，全片唯一男性参考）

链路：骨架(PIL COCO-18) → 820 zpose 副本(openpose ControlNet + Z-Image-Turbo-Fun)
     → ReActor 写 W 脸（按 y 位自动选索引：A1 上脸=W，B_LAST 下脸=W）→ h/w 闸门。

产物：examples/couple30_v1/keyframes/{KF_M,KF_A1,KF_A_LAST,KF_B_LAST}.png + report
"""
from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path

sys.stdout = io.TextIWRapper if False else io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

ROOT = Path(__file__).resolve().parents[1]
P820 = Path(__file__).resolve().parents[2] / "820"
sys.path.insert(0, str(P820))
sys.path.insert(0, str(P820 / "experiments"))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
import swap_face as sf  # noqa: E402
from experiments import rh_task  # noqa: E402
from experiments.metrics import FaceComparator  # noqa: E402

IDENT = ROOT / "examples" / "couple30_v1" / "identity"
KF = ROOT / "examples" / "couple30_v1" / "keyframes"
SKEL = KF / "skeletons"
REF_W = IDENT / "refs_extra" / "ref03.jpg"
W, H = 1200, 1600  # 竖屏 9:16

LIMBS = [
    (1, 2, (255, 0, 0)), (1, 5, (255, 85, 0)), (2, 3, (255, 170, 0)), (3, 4, (255, 255, 0)),
    (5, 6, (170, 255, 0)), (6, 7, (85, 255, 0)), (1, 8, (0, 255, 0)), (8, 9, (0, 255, 85)),
    (9, 10, (0, 255, 170)), (1, 11, (0, 255, 255)), (11, 12, (0, 170, 255)), (12, 13, (0, 85, 255)),
    (1, 0, (0, 0, 255)), (0, 14, (85, 0, 255)), (0, 15, (170, 0, 255)), (14, 16, (255, 0, 255)),
    (15, 17, (255, 0, 170)),
]


def draw_two(pts_a: dict, pts_b: dict, path: Path):
    img = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(img)
    for pts, jitter in ((pts_a, 0), (pts_b, 3)):
        p = {k: (x + jitter, y) for k, (x, y) in pts.items()}
        for i, j, c in LIMBS:
            if i in p and j in p:
                d.line([p[i], p[j]], fill=c, width=10)
        for k, (x, y) in p.items():
            r = 8 if k >= 14 else 10
            color = (255, 64, 64) if k < 14 else (153, 0, 102)
            d.ellipse([x - r, y - r, x + r, y + r], fill=color)
    img.save(path)
    print("[skel]", path.name)


def supine(hx, hy, face_up=True, far_wrist_raised=False):
    """侧视仰卧者（水平身体，头在左）。face_up=True 鼻尖朝上；False=俯卧鼻尖朝下。"""
    s = 1 if face_up else -1
    pts = {
        0: (hx + 26, hy + 22 * s),          # 鼻尖（朝上/朝下）
        1: (hx + 44, hy),                   # 颈
        2: (hx + 60, hy - 9), 5: (hx + 60, hy + 9),
        3: (hx + 140, hy - 12), 6: (hx + 140, hy + 12),
        4: (hx + 96, hy - 46 * s if not far_wrist_raised else hy - 46),
        7: (hx + 178, hy + 20),
        8: (hx + 268, hy - 9), 11: (hx + 268, hy + 9),
        9: (hx + 372, hy - 12), 12: (hx + 372, hy + 12),
        10: (hx + 470, hy - 10), 13: (hx + 470, hy + 10),
        14: (hx + 12, hy - 26 * s), 15: (hx + 12, hy + 26 * s),
        16: (hx + 30, hy - 24 * s), 17: (hx + 30, hy + 24 * s),
    }
    return pts


def build_skeletons():
    SKEL.mkdir(parents=True, exist_ok=True)
    # KF_A1: 男仰卧(下) + 女俯卧其上(上移45px)，头都在画面上部左侧，脸对脸
    mx, my = 300, 980          # 男头位置
    man = supine(mx, my, face_up=True)
    woman = supine(mx + 16, my - 45, face_up=False)  # 她俯卧，鼻尖朝下对准他的脸
    # 她的前臂撑在床头他头侧：手腕下拉
    woman[4] = (mx + 40, my - 6); woman[7] = (mx + 128, my - 4)
    draw_two(man, woman, SKEL / "sk_A1_prone.png")
    # KF_B_LAST: 反转——女仰卧(下) + 男俯卧支撑(上，手臂伸直不压她)
    wx, wy = 300, 1000
    woman_r = supine(wx, wy, face_up=True)
    man_r = supine(wx + 16, wy - 60, face_up=False)
    man_r[4] = (wx + 66, wy - 70); man_r[7] = (wx + 130, wy - 74)  # 直臂支撑不贴身
    draw_two(woman_r, man_r, SKEL / "sk_B_reversed.png")


SCENE = ("Sunday morning bedroom, soft warm light leaking through half-closed curtains, "
         "a cozy bed with rumpled white duvet. ")
W_ATTR = ("The woman has dark brown shoulder-length straight hair, a narrow oval face, "
          "fair cool skin, and wears a cream-white pajama set. ")
M_ATTR = ("The man is a Chinese man around 30, short black slightly messy hair, gentle "
          "bookish look, slim build, wearing a light grey long-sleeve pajama top and dark pants. ")
POS_A1 = ("Side view at bed level, perpendicular to both bodies, heads at the LEFT of the frame. "
          "THE MAN LIES FLAT ON HIS BACK on the bed, eyes closed, relaxed, arms loose. "
          "THE WOMAN LIES PRONE ON TOP OF HIM, chest on his chest, face to face with him, "
          "her nose pointing DOWN toward his face, foreheads nearly touching; her forearms "
          "rest on the bed beside his head; her legs lie along the outside of his legs. "
          "She looks at his sleeping face with a fond teasing smile. Both fully clothed, "
          "intimate but decent morning moment. Photorealistic, cinematic.")
POS_B = ("Same side view at bed level, heads at the LEFT of the frame. "
         "THE WOMAN NOW LIES ON HER BACK wrapped in the duvet, laughing, face up toward him. "
         "THE MAN LEANS OVER HER ON TOP supported on his straight arms, face down toward her, "
         "smiling mischievously, not pressing his weight on her, a hand gently touching her nose. "
         "Both fully clothed, playful intimate morning moment. Photorealistic, cinematic.")
NEG = ("nudity, nsfw, kiss close-up, extra limbs, fused bodies, extra legs, two women, two men, "
       "standing, sitting up, air gap between bodies, woman beside man not on top, deformed hands, "
       "blurry ugly bad, watermark, text")

ST = json.loads((P820 / "_zpose_state.json").read_text(encoding="utf-8"))
CID = ST["copy_id"]


def zimage(skel_png: Path | None, pos: str, seed: int) -> Path:
    """Z-Image-Turbo-Fun：有骨架走 controlnet，无骨架纯文本。返回本地 png。"""
    fmt = json.loads((P820 / "_zpose_apifmt.json").read_text(encoding="utf-8"))
    key = rh_task.load_api_key()
    if skel_png is not None:
        u_sk = rh_task.upload_file(key, str(skel_png))
        fmt["30"]["inputs"]["image"] = u_sk
        fmt["28"]["inputs"]["image"] = ["30", 0]
        fmt["28"]["inputs"]["strength"] = 1
        fmt.pop("39", None); fmt.pop("33", None)
        fmt["40"]["inputs"]["scale_to_length"] = 1920
    else:
        for n in ("28", "29", "30", "33", "39", "40"):
            fmt.pop(n, None)
        fmt["3"]["inputs"]["model"] = ["16", 0]
    fmt["6"]["inputs"]["text"] = pos
    fmt["7"]["inputs"]["text"] = NEG
    fmt["3"]["inputs"]["seed"] = seed
    fmt["3"]["inputs"]["steps"] = 15
    fmt["3"]["inputs"]["cfg"] = 1
    fmt["13"]["inputs"]["width"] = 1200
    fmt["13"]["inputs"]["height"] = 1600
    tid = rh_task.run_workflow_json(key, json.dumps(fmt, ensure_ascii=False), sandbox_id=CID)
    print("[zimage] task", tid, flush=True)
    while True:
        s = rh_task.task_status(key, tid)
        if s not in ("RUNNING", "QUEUED", "PENDING", "QUEUE"):
            print("[zimage] status", s, flush=True); break
        time.sleep(15)
    outs = rh_task.task_outputs(key, tid)
    urls = rh_task.collect_file_urls(outs)
    for u in urls:
        if u.lower().split("?")[0].endswith((".png", ".jpg", ".jpeg", ".webp")):
            dest = KF / f"_zimg_{seed}.png"
            rh_task.download(u, dest)
            print("[zimage] saved", dest.name)
            return dest
    raise SystemExit("zimage: no output")


_FC = FaceComparator()
_E_W = _FC.embed(_FC.largest_face(cv2.imread(str(REF_W))))


def faces_of(path: Path) -> list:
    img = cv2.imread(str(path))
    h, w = img.shape[:2]
    _FC.det.setInputSize((w, h))
    _, faces = _FC.det.detect(img)
    out = []
    if faces is None:
        return out
    for f in faces:
        box = (float(f[0]), float(f[1]), float(f[2]), float(f[3]))
        aligned = _FC.rec.alignCrop(img, f)
        cos = float(_FC.cosine(_FC.embed(aligned), _E_W))
        out.append({"box": box, "y_center": box[1] + box[3] / 2, "cos_vs_W": cos, "idx": len(out)})
    return sorted(out, key=lambda x: -x["box"][2] * x["box"][3])


def reactor_w(plate: Path, want_top: bool, tag: str) -> Path:
    """ReActor 写 W 脸：want_top=True 时目标是 y 更小的那张脸。自动纠正索引。"""
    faces = faces_of(plate)
    if not faces:
        raise RuntimeError(f"{plate.name}: no faces")
    target = min(faces, key=lambda f: f["y_center"]) if want_top else max(faces, key=lambda f: f["y_center"])
    # reactor 按检测顺序的 face index（node input_faces_index）→ 先试面积最大(=0)
    api = json.loads((P820 / "data" / "api_format" / "_reactor_single_c30.json").read_text(encoding="utf-8"))
    order = sorted(faces, key=lambda f: -f["box"][2] * f["box"][3])
    swap_idx = str(order.index(target))
    api["15"]["inputs"]["input_faces_index"] = swap_idx
    (P820 / "data" / "api_format" / f"_reactor_c30_{tag}.json").write_text(
        json.dumps(api, ensure_ascii=False), encoding="utf-8")
    sf.WORKFLOWS[f"reactor_{tag}"] = {
        "workflow_id": f"_reactor_c30_{tag}", "webapp_id": "",
        "ref": "2.image", "target": "1.image", "note": f"C2 KF swap face idx {swap_idx}"}
    meta = sf.run_swap(f"reactor_{tag}", plate, REF_W, tag=f"c30kf_{tag}", max_wait=600)
    outs = [Path(f) for f in meta.get("files", [])]
    outs = [f for f in outs if f.suffix.lower() == ".png"] or outs
    if not outs:
        raise RuntimeError("reactor no output")
    return outs[0]


def main() -> None:
    KF.mkdir(parents=True, exist_ok=True)
    build_skeletons()

    # 1) 男主锚（纯文本，无需骨架）
    m_pos = (SCENE + M_ATTR +
             "A waist-up portrait of him lying relaxed on a bed pillow, head slightly turned to his left, "
             "eyes closed with a faint peaceful smile, morning light on his face. "
             "Photorealistic, cinematic, sharp focus on face.")
    kf_m = zimage(None, m_pos, seed=20260917)
    kf_m.rename(KF / "KF_M_raw.png") if kf_m.exists() else None
    (KF / "KF_M.png").write_bytes((KF / "KF_M_raw.png").read_bytes()) if (KF / "KF_M_raw.png").exists() else None

    # 2) A1 首帧（骨架）
    a1 = zimage(SKEL / "sk_A1_prone.png", SCENE + W_ATTR + M_ATTR + POS_A1, seed=20260917)
    a1.replace(KF / "KF_A1_plate.png")
    out = reactor_w(KF / "KF_A1_plate.png", want_top=True, tag="a1")
    out.replace(KF / "KF_A1.png") if out.exists() else None

    # 3) B_LAST 反转锚（骨架）
    b = zimage(SKEL / "sk_B_reversed.png", SCENE + W_ATTR + M_ATTR + POS_B, seed=20260918)
    b.replace(KF / "KF_B_LAST_plate.png")
    out = reactor_w(KF / "KF_B_LAST_plate.png", want_top=False, tag="bl")
    out.replace(KF / "KF_B_LAST.png") if out.exists() else None

    # 4) 报告
    rows = []
    for name in ("KF_M", "KF_A1", "KF_B_LAST"):
        p = KF / f"{name}.png"
        if not p.exists():
            rows.append({"name": name, "verdict": "MISSING"}); continue
        fs = faces_of(p)
        rows.append({"name": name, "n_faces": len(fs),
                     "faces": [{"y": round(f["y_center"]), "cos_vs_W": round(f["cos_vs_W"], 3)} for f in fs]})
    (KF / "keyframes_report.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
