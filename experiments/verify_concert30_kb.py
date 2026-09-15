# -*- coding: utf-8 -*-
"""Verify the concert30 KB deposit reads back correctly."""
import sqlite3, io, sys, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
conn = sqlite3.connect(r'D:\qjcNetDiskDownload\deepseek-harness\project\820\data\kb.db')
conn.row_factory = sqlite3.Row
print('--- laws ---')
for r in conn.execute("SELECT code,name,substr(statement,1,40) s FROM boundary_laws WHERE attribution LIKE '%concert30%'"):
    print(r['code'], r['name'], '|', r['s'])
print('--- solutions ---')
for r in conn.execute("SELECT name,status,family,workflow_ref FROM expert_solutions WHERE name LIKE '%ref2va%' OR name LIKE '%reactor_role%'"):
    print(dict(r))
print('--- rules ---')
for r in conn.execute("SELECT code,tone,route,laws_json FROM decision_rules WHERE attribution LIKE '%concert30%'"):
    print(r['code'], r['tone'], r['route'], r['laws_json'])
print('--- chain repair solution detail ---')
sol = conn.execute("SELECT capabilities_json,route_json,metrics_json FROM expert_solutions WHERE name='reactor_role_chain_repair'").fetchone()
print('caps:', sol['capabilities_json'])
print('steps:', len(json.loads(sol['route_json'])))
print('metrics keys:', list(json.loads(sol['metrics_json']).keys()))
