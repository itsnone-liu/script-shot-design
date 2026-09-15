# -*- coding: utf-8 -*-
"""Verify the v3.2 KB deposit reads back correctly."""
import sqlite3, io, sys, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
conn = sqlite3.connect(r'D:\qjcNetDiskDownload\deepseek-harness\project\820\data\kb.db')
conn.row_factory = sqlite3.Row
print('--- new laws ---')
for r in conn.execute("SELECT code,name FROM boundary_laws WHERE attribution LIKE '%v3.2%'"):
    print(r['code'], r['name'])
print('--- solution versions ---')
for r in conn.execute("SELECT id,name,version,status,superseded_by FROM expert_solutions WHERE name IN ('ref2va_identity_recipe','reactor_role_chain_repair') ORDER BY name,version"):
    print(dict(r))
print('--- v2 route steps ---')
r = conn.execute("SELECT route_json FROM expert_solutions WHERE name='reactor_role_chain_repair' AND version=2").fetchone()
for s in json.loads(r['route_json']): print(' ', s['op'], '-', s['detail'][:60])
