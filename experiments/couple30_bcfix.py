# -*- coding: utf-8 -*-
"""couple30 v2.1: ReActor repair the B/C regens (probe runtime indices first).

For each of B_regen_00 / C_regen_00:
  - probe a representative window with idx0/idx1 x gender female/no
  - pick best W config, repair the full clip, measure
Outputs: B_regen_repaired.mp4 / C_regen_repaired.mp4 + probe report.

Usage: python -X utf8 experiments/couple30_bcfix.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

import couple30_repair as rep  # noqa: E402

OUT = rep.OUT

# probe windows: mid-clip where W face should be most frontal
# v2.7: B=regen4 (laugh-dense driving audio; harvest native laugh track)
B4 = OUT / "B_regen4_00.mp4"
B3 = OUT / "B_regen3_00.mp4"
C2 = OUT / "C_regen2_00.mp4"
BCFG = {
    "B": ({"src": B4, "win": (3.0, 5.5), "full": (0, 8.0),
           "out": "B_regen4_repaired.mp4"} if B4.exists()
          else {"src": B3, "win": (2.0, 5.0), "full": (0, 8.0),
                "out": "B_regen3_repaired.mp4"} if B3.exists()
          else {"src": B2, "win": (2.5, 5.0), "full": (0, 7.4),
                "out": "B_regen2_repaired.mp4"} if B2.exists()
          else {"src": OUT / "B_regen_00.mp4", "win": (2.5, 5.0), "full": (0, 7.0),
                "out": "B_regen_repaired.mp4"}),
    "C": ({"src": C2, "win": (5.0, 8.0), "full": (0, 13.7),
           "out": "C_regen2_repaired.mp4"} if C2.exists()
          else {"src": OUT / "C_regen_00.mp4", "win": (5.0, 8.0), "full": (0, 13.0),
                "out": "C_regen_repaired.mp4"}),
}
PROBE = BCFG
STATE = OUT / "bcfix_state.json"


def probe(seg: str, cfg: dict, results: dict) -> dict:
    src, (t0, t1) = cfg["src"], cfg["win"]
    best = {"w": -1.0}
    for idx in (0, 1):
        for gender in ("female", "no"):
            tag = f"p_{seg}_{idx}_{gender}"
            outs = rep.run_reactor(src, idx, tag, gender=gender)
            if not outs:
                continue
            m = rep.measure(outs[0])
            w = m.get("w_median") or -1
            print(f"[{seg}] idx{idx}/{gender}: w_median={w} min={m.get('w_min')} "
                  f"m_dmg={m.get('m_damaged_faces')}", flush=True)
            results[f"{seg}:{idx}:{gender}"] = m
            if w > best["w"]:
                best = {"w": w, "idx": idx, "gender": gender}
    return best


def main() -> int:
    results = {}
    st = json.loads(STATE.read_text(encoding="utf-8-sig")) if STATE.exists() else {}
    for seg, cfg in PROBE.items():
        if seg in st and (OUT / cfg["out"]).exists():
            print(f"[{seg}] already repaired, skip")
            continue
        best = probe(seg, cfg, results)
        if "idx" not in best:
            print(f"[{seg}] probe found nothing — keep regen as-is")
            continue
        print(f"[{seg}] best: idx{best['idx']} gender={best['gender']} "
              f"w={best['w']:.3f} -> full repair", flush=True)
        f0, f1 = cfg["full"]
        # run_reactor processes whole clip; crop to full range then measure
        outs = rep.run_reactor(cfg["src"], best["idx"], f"r_{seg}",
                               gender=best["gender"])
        dest = OUT / cfg["out"]
        if outs:
            import shutil
            shutil.copyfile(outs[0], dest)
            m = rep.measure(dest)
            print(f"[{seg}] repaired measure:", json.dumps(m, ensure_ascii=False))
            st[seg] = {"idx": best["idx"], "gender": best["gender"],
                       "probe_w": best["w"], "measure": m}
            STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1),
                             encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
