# -*- coding: utf-8 -*-
"""C2 尾帧生产：A_LAST / C_LAST —— 已批准帧小步编辑 + ReActor 逐 index 校准。

A_LAST: 基于 KF_A1_corrected（女方俯身上方）。剧情=捏鼻升级：女方右手轻捏男方鼻尖，
        带胜利笑意；男方闭眼忍笑。
C_LAST: 基于 KF_B_LAST_corrected（男上女下）。剧情=落幅：男方食指轻碰女方鼻尖，
        两人对视微笑，鼻尖接近。

验证规则（硬）：目标脸（按 y 位识别=图像内容，非 ReActor 顺序）cos>=0.45 且
另一脸 cos<0.40（W 的脸不得写到男方）。两个 index 候选 [1,0] 依次实跑。
"""
from __future__ import annotations
import io, json, sys, time
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
ROOT = Path(__file__).resolve().parents[1]
P820 = ROOT.parent / "820"
KF = ROOT / "examples/couple30_v1/keyframes"
REF = ROOT / "examples/couple30_v1/identity/refs_extra/ref03.jpg"
sys.path.insert(0, str(P820)); sys.path.insert(0, str(P820 / "experiments"))
import cv2
import swap_face as sf
from experiments import rh_task
from experiments.metrics import FaceComparator

WEBAPP = "2075052610570244098"
fc = FaceComparator(); e_w = fc.embed(fc.largest_face(cv2.imread(str(REF))))

BASE = ("图一是已确认的关键帧。只做指定的小改动，严格保持两个人的身份、脸型、发型、"
        "服装、床铺、构图、体位、光线和背景完全不变；不要重新设计人物，不要改变镜头，"
        "不要增加人物，不要改变任何人的脸型。")
TASKS = {
    "A_LAST": dict(
        src=KF / "KF_A1_corrected.png",
        prompt=BASE + "女方抬起右手，手指轻轻捏住男方的鼻尖，她自己带着得意的笑容；"
                      "男方依旧闭着眼，嘴角忍着笑。除此之外一切不变。"),
    "C_LAST": dict(
        src=KF / "KF_B_LAST_corrected.png",
        prompt=BASE + "男方伸出右手食指，轻轻碰一下女方的鼻尖，两人对视微笑；"
                      "两人的鼻尖距离很近但不要接触。除此之外一切不变。"),
}
# 目标脸识别：A_LAST 女方在上方(min y)；C_LAST 女方在下方(max y)
INTENT = {"A_LAST": "top", "C_LAST": "bottom"}


def klein(name: str, src: Path, prompt: str) -> Path:
    key = rh_task.load_api_key()
    u = rh_task.upload_file(key, str(src))
    nodes = [{"nodeId": "597", "fieldName": "image", "fieldValue": u},
             {"nodeId": "598", "fieldName": "image", "fieldValue": u},
             {"nodeId": "500", "fieldName": "text", "fieldValue": prompt}]
    tid = rh_task.run_webapp(key, WEBAPP, nodes)
    print(f"[klein] {name} task {tid}", flush=True)
    for _ in range(3):
        while True:
            s = rh_task.task_status(key, tid)
            if s not in ("RUNNING", "QUEUED", "PENDING", "QUEUE"):
                break
            time.sleep(15)
        if s == "SUCCESS":
            break
        print(f"[klein] {name} status {s} retry", flush=True)
        time.sleep(10)
    if s != "SUCCESS":
        raise RuntimeError(f"{name} klein failed: {s}")
    urls = rh_task.collect_file_urls(rh_task.task_outputs(key, tid))
    for u2 in urls:
        if u2.lower().split("?")[0].endswith((".png", ".jpg", ".jpeg", ".webp")):
            dest = KF / f"{name}_k.png"; rh_task.download(u2, dest)
            print(f"[klein] saved {dest.name}", flush=True); return dest
    raise RuntimeError("klein no image")


def detect(path: Path):
    img = cv2.imread(str(path)); h, w = img.shape[:2]
    fc.det.setInputSize((w, h)); _, faces = fc.det.detect(img)
    arr = []
    if faces is not None:
        for f in faces:
            cos = float(fc.cosine(fc.embed(fc.rec.alignCrop(img, f)), e_w))
            arr.append(dict(x=round(float(f[0])), y=round(float(f[1])),
                            w=round(float(f[2])), h=round(float(f[3])), cos=round(cos, 4)))
    return sorted(arr, key=lambda z: z["w"] * z["h"], reverse=True)


def score(faces, intent):
    """返回 (pass, intended_cos, other_cos)。目标脸按 y 位选，双人帧要求两脸都在。"""
    if len(faces) < 2:
        return False, None, None
    tgt = min(faces, key=lambda f: f["y"]) if intent == "top" else max(faces, key=lambda f: f["y"])
    other = [f for f in faces if f is not tgt][0]
    return (tgt["cos"] >= 0.45 and other["cos"] < 0.40), tgt["cos"], other["cos"]


def reactor(name: str, plate: Path, idx: int):
    api = json.loads((P820 / "data/api_format/_reactor_single_c30.json").read_text(encoding="utf-8"))
    api["15"]["inputs"]["input_faces_index"] = str(idx)
    api["15"]["inputs"]["face_restore_visibility"] = 0.25
    wf = f"_reactor_tail_{name}_{idx}"
    (P820 / f"data/api_format/{wf}.json").write_text(json.dumps(api, ensure_ascii=False), encoding="utf-8")
    sf.WORKFLOWS[wf] = {"workflow_id": wf, "webapp_id": "", "ref": "2.image", "target": "1.image",
                        "note": f"tail {name} idx {idx}"}
    meta = sf.run_swap(wf, plate, REF, tag=f"c30_tail_{name}_{idx}", max_wait=600)
    files = [Path(x) for x in meta.get("files", []) if Path(x).suffix.lower() == ".png"]
    if not files:
        raise RuntimeError("reactor no output")
    out = KF / f"{name}_idx{idx}.png"; out.write_bytes(files[0].read_bytes())
    return out


def main():
    report = []
    for name, spec in TASKS.items():
        plate = klein(name, spec["src"], spec["prompt"])
        faces0 = detect(plate)
        print(f"[plate] {name} faces={json.dumps(faces0)}", flush=True)
        done = None
        for idx in (1, 0):  # 校准结论优先 idx=1
            out = reactor(name, plate, idx)
            faces = detect(out)
            ok, tcos, ocos = score(faces, INTENT[name])
            print(f"[swap] {name} idx={idx} faces={json.dumps(faces)} pass={ok}", flush=True)
            report.append(dict(name=name, idx=idx, faces=faces, ok=ok,
                               intended_cos=tcos, other_cos=ocos))
            if ok:
                out.replace(KF / f"KF_{name}_corrected.png")
                done = idx; break
        if done is None:
            print(f"[FAIL] {name} no index passed — manual review", flush=True)
        else:
            print(f"[OK] {name} idx={done} -> KF_{name}_corrected.png", flush=True)
    (KF / "tail_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
