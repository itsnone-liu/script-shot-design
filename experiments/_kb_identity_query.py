# -*- coding: utf-8 -*-
"""Print knowledge cards for the identity workflow candidates."""
import io
import json
import sqlite3
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
DB = r"D:\qjcNetDiskDownload\deepseek-harness\project\820\data\kb.db"

CANDIDATES = [
    "1940886562836213761",  # Flux Kontext consistent characters
    "2030608514263031810",  # 参考图一键设计人物角色
    "2033184363063545858",  # 单图生成多图
    "2061315379338764290",  # seedance2.0 角色卡
    "1930656665035845633",  # InstantID+PuLID 换脸
    "1920447051887214593",  # InstantID
    "2054763247810686977",  # 分镜出图
]

db = sqlite3.connect(DB)
cur = db.cursor()

for rh_id in CANDIDATES:
    wfs = cur.execute(
        "SELECT id, title, raw_dir, graph_path FROM workflows WHERE source_id=?",
        (rh_id,),
    ).fetchall()
    for wid, title, raw_dir, graph_path in wfs:
        print("=" * 80)
        print(f"[{rh_id}] {title}  (wf_id={wid}, nodes graph={graph_path})")
        cards = cur.execute(
            "SELECT model_name, capabilities_json, input_json, output_json, use_case, limitation, summary_text "
            "FROM knowledge_cards WHERE workflow_id=?",
            (wid,),
        ).fetchall()
        if not cards:
            print("  (no knowledge card)")
        for model, caps, inp, outp, use, lim, summary in cards:
            print(f"  model: {model}")
            print(f"  caps : {caps}")
            print(f"  input: {inp}")
            print(f"  out  : {outp}")
            print(f"  use  : {(use or '')[:200]}")
            print(f"  lim  : {(lim or '')[:200]}")
            print(f"  sum  : {(summary or '')[:300]}")
