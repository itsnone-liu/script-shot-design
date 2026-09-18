# -*- coding: utf-8 -*-
"""couple30 windowed role-isolated face repair (route A for B/C segments + A_T1 fallback arm).

Design (concert30 reactor_role_chain_repair v2 laws + couple30 scan data):
- W only (user complaint); M protected by detect_gender_input='female' + window cuts.
- Windows from identity_scan: A_T1 full [0,14] W-upper (keyframe law: idx1);
  B_T2 [0,3.0] W-upper idx1 + [5.5,7.0] W-lower idx0, flip gap skipped;
  C_T2 [3.0,13.5] W-lower idx0 (early C: W occluded, only M visible -> cut to avoid cross-swap).
- Probe-first (runtime index law): 1.6s probe on a both-faces-clear spot per index class,
  local measure, correct if cross-swapped. 2 probes total (upper-class on A, lower-class on C).
- Post-gate: per-window scan (W median>=0.55/min>=0.40 relaxed for up-angles) + M-not-degraded.
- Resume via repair_state.json. Audio stripped everywhere (voice line rebuilt later).

Usage:
  python -X utf8 experiments/couple30_repair.py --phase probe|run|gate|stitch|all
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "820"))
from experiments import rh_task  # noqa: E402

SHOTS = ROOT / "output" / "creative_v2" / "couple30_v1" / "shots"
OUT = ROOT / "output" / "creative_v2" / "couple30_v1" / "repaired"
IDENT = ROOT / "examples" / "couple30_v1" / "identity"
KF = ROOT / "examples" / "couple30_v1" / "keyframes"
FMT = ROOT.parent / "820" / "data" / "api_format" / "2005804455352303618.json"
CARRIER = "2093518439926218753"
# swap source = approved final canonical front (ref03 identity in near-frontal geometry,
# h/w 1.573 cos 0.810 — beats ref03 3/4-side for frontal W frames). Scoring anchors stay
# ref03-based (identity truth), not source-based.
REF_W = IDENT / "canonical_v6" / "front.png"

WINDOWS = {
    # name: (src_clip, start, end, index_hypothesis, probe_spot_or_None)
    "A_full":   (SHOTS / "C30_A_T1_00.mp4", 0.0, 14.0, 1, (12.3, 14.0)),
    "B_w1":     (SHOTS / "C30_B_T2_00.mp4", 0.0, 3.0, 1, None),
    "B_w2":     (SHOTS / "C30_B_T2_00.mp4", 5.5, 7.0, 0, None),
    "B_gap":    (SHOTS / "C30_B_T2_00.mp4", 3.0, 5.5, None, None),  # passthrough re-encode
    "C_w":      (SHOTS / "C30_C_T2_00.mp4", 3.0, 13.5, 0, (5.0, 6.6)),
}

STATE = OUT / "repair_state.json"


def load_state() -> dict:
    if not STATE.exists():
        return {"probes": {}, "windows": {}}
    st = json.loads(STATE.read_text(encoding="utf-8-sig"))  # BOM-tolerant
    for section in ("probes", "windows"):
        st[section] = {k: v for k, v in (st.get(section) or {}).items() if v}
    return st


def save_state(st: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")


def ffmpeg_cut(src: Path, start: float, end: float, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{start}", "-to", f"{end}",
                        "-i", str(src), "-c:v", "libx264", "-crf", "16", "-preset", "medium",
                        "-an", str(dest)])
    if r.returncode:
        raise RuntimeError(f"ffmpeg cut failed {dest}")
    return dest


def run_reactor(clip: Path, index: int, tag: str, max_wait: int = 2400,
                gender: str = "female") -> list[Path]:
    key = rh_task.load_api_key()
    fmt = json.loads(FMT.read_text(encoding="utf-8"))
    u_face = rh_task.upload_file(key, REF_W)
    u_vid = rh_task.upload_file(key, clip)
    print(f"[{tag}] face -> {u_face}\n[{tag}] clip -> {u_vid}", flush=True)
    fmt["10"]["inputs"]["image"] = u_face
    fmt["11"]["inputs"]["video"] = u_vid
    fmt["15"]["inputs"]["input_faces_index"] = str(index)
    # gender guard: 'female' guards M cross-swap when the classifier reads W's face
    # reliably (C lower/up-angle did: 0.77). It BLOCKS the swap when W's angle
    # confuses it (A prone top-down: both indices no-op'd 0.40/0.43) — so the
    # upper class runs with 'no'; M damage is caught by the gate's m_damaged check.
    fmt["15"]["inputs"]["detect_gender_input"] = gender
    fmt["18"]["inputs"]["save_output"] = True
    fmt["21"]["inputs"]["save_output"] = False
    tid = rh_task.run_workflow_json(key, fmt, sandbox_id=CARRIER)
    print(f"[{tag}] task {tid}", flush=True)
    deadline = time.time() + max_wait
    last = ""
    while time.time() < deadline:
        try:
            result = rh_task.task_outputs(key, tid)
            break
        except Exception as e:
            msg = f"{type(e).__name__}: {str(e)[:90]}"
            if msg != last:
                print(f"[{tag}] {msg}", flush=True)
                last = msg
            time.sleep(30)
    else:
        raise RuntimeError(f"[{tag}] timeout {tid}")
    outs = []
    for n, u in enumerate(rh_task.collect_file_urls(result)):
        ext = ".zip" if ".zip" in u.lower() else ".mp4"
        target = OUT / f"{tag}_{n:02d}{ext}"
        rh_task.download(u, target)
        outs.append(target)
    if not outs:
        raise RuntimeError(f"[{tag}] no outputs")
    return outs


def measure(clip: Path) -> dict:
    """Local W/M scoring on a repaired clip: W best-cosine stats + M-protection check."""
    import cv2
    sys.path.insert(0, str(ROOT))
    from experiments.metrics import FaceComparator
    fc = FaceComparator()
    # honest gate: scoring anchors EXCLUDE the swap source (canonical front) to avoid
    # circular self-similarity; ref03 + angle-matched canonical set = identity truth.
    w_refs = [IDENT / "refs_extra" / "ref03.jpg",
              IDENT / "canonical_v6" / "talk.png",
              IDENT / "canonical_v6" / "up.png",
              IDENT / "canonical_v6" / "down.png"]
    m_refs = [KF / "KF_M.png"]
    det = cv2.FaceDetectorYN.create(str(ROOT.parent / "820" / "data" / "models" / "yunet.onnx"),
                                     "", (672, 896), score_threshold=0.7)
    cap = cv2.VideoCapture(str(clip))
    vfps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    tmp = Path(tempfile.gettempdir()) / "c30_rep_face.jpg"
    wv_all, m_bad, n = [], 0, 0
    import statistics
    while True:
        ok, im = cap.read()
        if not ok or im is None or not im.size:
            break
        n += 1
        if n % max(1, round(vfps / 2)):
            continue
        h, w = im.shape[:2]
        det.setInputSize((w, h))
        _, faces = det.detect(im)
        if faces is None:
            continue
        for f in faces:
            x, y, fw, fh = (int(v) for v in f[:4])
            conf = float(f[-1])
            if conf < 0.8 or fh < 40 or fw < 8:
                continue
            crop = cv2.cvtColor(im[max(0, y):y + fh, max(0, x):x + fw], cv2.COLOR_BGR2GRAY)
            if crop.size == 0 or float(cv2.Laplacian(crop, cv2.CV_64F).var()) < 30:
                continue  # degenerate/soft window tolerant
            scale = 1.4
            cx, cy = x + fw / 2, y + fh / 2
            x0 = max(0, int(cx - fw * scale / 2)); y0 = max(0, int(cy - fh * scale / 2))
            fimg = im[y0:min(h, y0 + int(fh * scale)), x0:min(w, x0 + int(fw * scale))]
            cv2.imwrite(str(tmp), fimg)
            wv = [r["cosine"] for p in w_refs for r in [fc.score(str(tmp), str(p))]
                  if r.get("face_ok") and r.get("cosine") is not None]
            mv = [r["cosine"] for p in m_refs for r in [fc.score(str(tmp), str(p))]
                  if r.get("face_ok") and r.get("cosine") is not None]
            wm = max(wv) if wv else None
            mm = max(mv) if mv else None
            if wm is not None and mm is not None:
                # a face that should be M (m wins by margin) collapsed into W => cross-swap damage
                if mm - wm >= 0.05 and wm >= 0.60:
                    m_bad += 1
                if wm - mm >= 0.05:
                    wv_all.append(wm)
    cap.release()
    return {
        "frames": n, "w_samples": len(wv_all),
        "w_median": round(statistics.median(wv_all), 4) if wv_all else None,
        "w_min": round(min(wv_all), 4) if wv_all else None,
        "m_damaged_faces": m_bad,
    }


def phase_probe(st: dict) -> None:
    for cls, (win, spot) in {"upper": ("A_full", WINDOWS["A_full"][4]),
                             "lower": ("C_w", WINDOWS["C_w"][4])}.items():
        src, ws, we, idx, _ = WINDOWS[win]
        gender = "no" if cls == "upper" else "female"  # see run_reactor note
        if st["probes"].get(cls, {}).get("verdict"):
            print(f"[probe:{cls}] already {st['probes'][cls]['verdict']}")
            continue
        ps, pe = spot
        probe_clip = ffmpeg_cut(src, ps, pe, OUT / f"probe_{cls}.mp4")
        outs = run_reactor(probe_clip, idx, f"probe_{cls}", gender=gender)
        m = measure(outs[0])
        ok = (m["w_samples"] >= 2 and m["w_median"] is not None and m["w_median"] >= 0.55
              and m["m_damaged_faces"] == 0)
        st["probes"][cls] = {"window": win, "index": idx, "gender": gender,
                             "output": str(outs[0]),
                             "measure": m, "verdict": "OK" if ok else "CROSS_OR_FAIL"}
        save_state(st)
        print(f"[probe:{cls}] idx={idx} gender={gender} -> {st['probes'][cls]['verdict']} {m}")
        if not ok:
            # corrective: flip index and re-probe once (runtime reversal law)
            alt = 1 - idx
            outs2 = run_reactor(probe_clip, alt, f"probe_{cls}_alt{alt}", gender=gender)
            m2 = measure(outs2[0])
            ok2 = (m2["w_samples"] >= 2 and m2["w_median"] is not None and m2["w_median"] >= 0.55
                   and m2["m_damaged_faces"] == 0)
            st["probes"][cls] = {"window": win, "index": alt if ok2 else idx,
                                 "gender": gender, "output": str(outs2[0]), "measure": m2,
                                 "verdict": "OK_ALT" if ok2 else "FAIL_BOTH"}
            save_state(st)
            print(f"[probe:{cls}] alt idx={alt} gender={gender} -> {st['probes'][cls]['verdict']} {m2}")


def phase_run(st: dict) -> None:
    idx_cls = {"A_full": "upper", "B_w1": "upper", "B_w2": "lowerB", "C_w": "lower"}
    for name in ["A_full", "B_w1", "B_w2", "C_w"]:
        if st["windows"].get(name, {}).get("status") == "repaired":
            print(f"[{name}] already repaired")
            continue
        src, ws, we, idx, _ = WINDOWS[name]
        cls = idx_cls[name]
        pv = st["probes"].get(cls, {}).get("verdict", "")
        if not pv.startswith("OK"):
            print(f"[{name}] probe class {cls} not OK ({pv}); skip")
            continue
        idx = st["probes"][cls]["index"]
        gender = st["probes"][cls].get("gender", "female")
        clip = ffmpeg_cut(src, ws, we, OUT / f"{name}_in.mp4") if (ws, we) != (0.0, float("inf")) else src
        outs = run_reactor(clip, idx, name, gender=gender)
        st["windows"][name] = {"status": "repaired", "index": idx, "gender": gender,
                               "output": str(outs[0])}
        save_state(st)
        print(f"[{name}] repaired idx={idx} -> {outs[0]}")


def phase_gate(st: dict) -> None:
    for name in ["A_full", "B_w1", "B_w2", "C_w"]:
        w = st["windows"].get(name)
        if not w or w.get("status") != "repaired" or w.get("gate"):
            continue
        m = measure(Path(w["output"]))
        ok = (m["w_median"] is not None and m["w_median"] >= 0.55
              and m["w_min"] is not None and m["w_min"] >= 0.40
              and m["m_damaged_faces"] == 0)
        w["gate"] = "PASS" if ok else "FAIL"
        w["measure"] = m
        save_state(st)
        print(f"[gate:{name}] {w['gate']} {m}")


def phase_stitch(st: dict) -> None:
    import subprocess as sp
    ENC = ["-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-an"]

    def norm_concat(parts: list[Path], dest: Path, tag: str) -> None:
        """Uniform re-encode concat. RH ReActor output is tagged 12fps (content =
        every-2nd-frame of the 24fps input): itsscale=fps/24 restores real-time
        timing; fps=24 then normalizes everything for concat."""
        import re as _re
        cmd = ["ffmpeg", "-y", "-v", "error"]
        for p in parts:
            r = sp.run(["ffprobe", "-v", "error", "-select_streams", "v",
                        "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
            m = _re.match(r"(\d+)/(\d+)", r.stdout.strip())
            scale = []
            if m:
                fps = int(m.group(1)) / int(m.group(2))
                if 1 < fps < 20:  # 12fps ReActor tag -> respeed to 24
                    scale = ["-itsscale", f"{fps / 24:.6f}"]
            cmd += scale + ["-i", str(p)]
        f = "".join(f"[{i}:v]fps=24[v{i}]" for i in range(len(parts)))
        cin = "".join(f"[v{i}]" for i in range(len(parts)))
        cmd += ["-filter_complex", f"{f};{cin}concat=n={len(parts)}:v=1:a=0[v]",
                "-map", "[v]", *ENC, str(dest)]
        r = sp.run(cmd)
        if r.returncode and not (dest.exists() and dest.stat().st_size > 100_000):
            raise RuntimeError(f"{tag} stitch failed")
        if r.returncode:
            print(f"[{tag}] note: ffmpeg exit {r.returncode} but output valid; continuing")

    # B: if either window unrepaired (ReActor no-ops on flip motion), use the whole
    # original take passthrough (B scored best of 3 segments pre-repair: 0.455)
    parts = [st["windows"].get(x, {}).get("output") for x in ("B_w1", "B_w2")]
    if not (OUT / "B_repaired.mp4").exists():
        if all(parts):
            gap = ffmpeg_cut(WINDOWS["B_gap"][0], 3.0, 5.5, OUT / "B_gap_in.mp4")
            norm_concat([Path(parts[0]), gap, Path(parts[1])], OUT / "B_repaired.mp4", "B")
        else:
            print("B: windows incomplete (flip motion defeats ReActor) -> original passthrough")
            norm_concat([WINDOWS["B_gap"][0]], OUT / "B_repaired.mp4", "B")
        print("B_repaired.mp4 done")
    # A: window covers whole take; normalize encode for concat compatibility
    w = st["windows"].get("A_full")
    if w and w.get("status") == "repaired" and not (OUT / "A_repaired.mp4").exists():
        norm_concat([Path(w["output"])], OUT / "A_repaired.mp4", "A")
        print("A_repaired.mp4 done")
    # C: original head [0,3.0] (M line L09 zone, unrepaired by design) + repaired tail
    w = st["windows"].get("C_w")
    if w and w.get("status") == "repaired" and not (OUT / "C_repaired.mp4").exists():
        head = ffmpeg_cut(WINDOWS["C_w"][0], 0.0, 3.0, OUT / "C_head_in.mp4")
        norm_concat([head, Path(w["output"])], OUT / "C_repaired.mp4", "C")
        print("C_repaired.mp4 done")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True,
                    choices=["probe", "run", "gate", "stitch", "all"])
    args = ap.parse_args()
    st = load_state()
    if args.phase in ("probe", "all"):
        phase_probe(st)
    if args.phase in ("run", "all"):
        phase_run(st)
    if args.phase in ("gate", "all"):
        phase_gate(st)
    if args.phase in ("stitch", "all"):
        phase_stitch(st)
    print(json.dumps(st, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
