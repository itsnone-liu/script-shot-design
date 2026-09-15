# -*- coding: utf-8 -*-
"""Deposit concert30 v3.2 lessons into 820's ComfyUI workflow KB.

- boundary_laws: 3 new laws (costume bleed / runtime face index / take selection)
- expert_solutions: version-2 rows for ref2va_identity_recipe and reactor_role_chain_repair
  (v1 rows marked superseded with superseded_by linkage, per the M15 lifecycle)
Idempotent; backs up kb.db first."""
from __future__ import annotations
import json, shutil, sqlite3, sys
from datetime import datetime
from pathlib import Path

P820 = Path(r'D:\qjcNetDiskDownload\deepseek-harness\project\820')
DB = P820 / 'data' / 'kb.db'
DOC = '821/knowledge/IDENTITY_HYBRID_PIPELINE_V1.md'

def backup():
    stamp = datetime.now().strftime('%Y%m%d')
    bak = P820 / 'data' / f'kb.db.bak-{stamp}-preConcert30v32'
    if not bak.exists():
        shutil.copy2(DB, bak); print(f'backup -> {bak.name}')
    else:
        print(f'backup exists: {bak.name}')

def next_code(conn, table, prefix):
    used = {r['code'] for r in conn.execute(f"SELECT code FROM {table} WHERE code LIKE '{prefix}%'")}
    n = 100
    while f'{prefix}-{n}' in used: n += 1
    return f'{prefix}-{n}'

def insert_laws(conn):
    laws = [
        ('服装渗色律', '全身照参考会把服装带进生成画面；要身份锚又要控服装，用人脸裁切替换全身照并加服装硬约束。',
         '参考图注意力不分身份与穿着；服装约束必须显式（"never copy clothing from the reference photos"）。人脸裁切保留几何锚同时让服装不可见。',
         'concert30 v3.1→v3.2：S2 生成出现酒红上衣=ref01 红裙全身照渗色；换裁切+约束后黑衣 ✓ 身份 0.582→0.722'),
        ('运行时人脸序号律', 'ReActor 运行时的脸序号与外部检测脚本的排序可能相反；链修前必须先跑一刀并测中间产物确认真实索引。',
         'YuNet 按面积排序，ReActor 内部检测排序规则不同且逐帧可变；盲跑链修=交叉换脸。正确流程：单刀修复→本地测量→定索引→补第二刀。',
         'concert30 S6v4：脚本判他=0 她=1，盲链修致她脸拿到 H 源（0.30-0.38）；修正刀序后她 0.75-0.81 全片最高'),
        ('生成方差择优律', '同配方生成任务的身份分数方差大；预算内抽两版择优+剪辑跳过弱帧，优于反复重试。',
         '扩散采样随机性导致同提示词产出身份质量波动（实测同配方 0.55/0.73）；弱帧常集中在片段首尾（转身/入画），剪辑 trim 即可绕开。',
         'concert30 S2 v5/v6 两版对比；v6 开场 1.2s 弱段 trim 后窗口 0.722'),
    ]
    codes = {}
    for name, statement, technical, evidence in laws:
        if conn.execute("SELECT 1 FROM boundary_laws WHERE name=?", (name,)).fetchone():
            print('law exists:', name); continue
        code = next_code(conn, 'boundary_laws', 'BL')
        conn.execute("INSERT INTO boundary_laws (code,name,statement,technical,evidence,status,attribution) VALUES (?,?,?,?,?,'law',?)",
                     (code, name, statement, technical, evidence, 'concert30 v3.2 实证 (821)'))
        codes[name] = code; print('law inserted:', code, name)
    return codes

def insert_solution_v2(conn, name, cols):
    row = conn.execute("SELECT id,version FROM expert_solutions WHERE name=? ORDER BY version DESC LIMIT 1", (name,)).fetchone()
    if not row:
        print('missing v1 for', name); return None
    v1_id, v1_ver = row['id'], row['version']
    if conn.execute("SELECT 1 FROM expert_solutions WHERE name=? AND version=?", (name, v1_ver + 1)).fetchone():
        print('solution v2 exists:', name); return v1_id
    conn.execute("""INSERT INTO expert_solutions
        (name,version,status,family,requirements,capabilities_json,route_json,workflow_ref,
         applicable_conditions,limitations,key_params_json,metrics_json,cost_json,
         success_cases_json,failure_cases_json,evidence_note,source,superseded_by)
        VALUES (:name,:version,'candidate',:family,:requirements,:capabilities_json,:route_json,:workflow_ref,
                :applicable_conditions,:limitations,:key_params_json,:metrics_json,:cost_json,
                :success_cases_json,:failure_cases_json,:evidence_note,:source,NULL)""", cols)
    v2_id = conn.execute("SELECT id FROM expert_solutions WHERE name=? ORDER BY version DESC LIMIT 1", (name,)).fetchone()['id']
    conn.execute("UPDATE expert_solutions SET status='superseded', superseded_by=?, updated_at=datetime('now') WHERE id=?", (v2_id, v1_id))
    print(f'solution v2 inserted: {name} (v1 id={v1_id} -> superseded)')
    return v2_id

def main():
    if not DB.exists(): sys.exit(f'missing {DB}')
    backup()
    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row

    insert_laws(conn)

    insert_solution_v2(conn, 'ref2va_identity_recipe', {
        'name': 'ref2va_identity_recipe', 'version': 2, 'family': 'video_identity_gen',
        'requirements': '真实人物出演AI视频 参考图身份一致 服装可控 真人长相不变 identity consistency costume control',
        'capabilities_json': json.dumps(['identity_transfer', 'structure_preserve']),
        'route_json': json.dumps([
            {'step': 1, 'op': 'build_ref_pack_v5', 'detail': 'Picture1=确定性人脸裁切锚；其余参考一律用验证过本人的裁切或单人图；全身照只在需要服装时用（否则渗色）'},
            {'step': 2, 'op': 'configure', 'detail': 'int8 UNET + SameFace_Fix 0.5 + turbo_6step + 1344x768'},
            {'step': 3, 'op': 'prompt', 'detail': '参考图职责声明 + 硬属性（眼镜/发型/V形尖下巴/偏小眼不放大）+ 服装硬约束(plain black top / never copy reference clothing) + 单一连续场景 + action_mandate + 禁区清单'},
            {'step': 4, 'op': 'take_select', 'detail': '预算内抽两版择优；剪辑 trim 掉首尾弱帧'},
            {'step': 5, 'op': 'gate', 'detail': '角色窗口密采样 median>=0.60；漂移转 reactor 修复链'}]),
        'workflow_ref': 'runninghub:2093518439926218753',
        'applicable_conditions': '有 4+ 张清晰日常照的真人；需要跨段服装连续性；4-15s；<=9 参考图',
        'limitations': '身份-动作交换律仍适用；同配方方差大（0.55-0.73 实测）需择优；蒙太奇必漂移',
        'key_params_json': json.dumps({'sameface_fix': 0.5, 'pack': 'face-crop anchor + verified crops; no costume-bearing photos', 'geometry_attrs': 'pointed V chin, small eyes, no beautification', 'costume_rule': 'explicit, never-copy-references'}),
        'metrics_json': json.dumps({'S2_black_top_v6': {'girl_window_median': 0.722, 'max': 0.777}, 'S6_pair_plate_prepair': {'girl_vs_grefs': '0.58-0.70'}, 'sface_same_person_threshold': 0.363}),
        'cost_json': json.dumps({'coins_per_5s': 47, 'minutes': '8-10'}),
        'success_cases_json': json.dumps(['concert30 v3.2 定稿：女生五窗 0.722/0.770/0.767/0.750/0.776']),
        'failure_cases_json': json.dumps(['v3.1 S2 红裙渗色（pack v4 全身照）', 'v5 单版身份 0.55（方差）']),
        'evidence_note': f'concert30 v3.2；完整叙述见 {DOC} §8.2', 'source': 'agent_composed'})

    insert_solution_v2(conn, 'reactor_role_chain_repair', {
        'name': 'reactor_role_chain_repair', 'version': 2, 'family': 'face_swap',
        'requirements': '生成视频换回真人脸 双人同框各自保身份 修复链 face swap video two-person',
        'capabilities_json': json.dumps(['identity_transfer', 'expression_preserve', 'structure_preserve']),
        'route_json': json.dumps([
            {'step': 1, 'op': 'role_map_hint', 'detail': 'YuNet+SFace 扫描底片得"时间→角色"表（仅作窗口切分参考，索引不直接采信）'},
            {'step': 2, 'op': 'probe_pass', 'detail': '每窗先跑一刀主角色修复，立即本地测量中间产物——确定 ReActor 运行时真实索引'},
            {'step': 3, 'op': 'second_pass', 'detail': '按实测索引补第二刀（另一角色），测 girl/hua 双分确认无交叉'},
            {'step': 4, 'op': 'post', 'detail': 'RIFE 半速 → setpts=PTS/2 + fps=24；窗口 concat 无痕拼回'}]),
        'workflow_ref': 'runninghub:2005804455352303618',
        'applicable_conditions': '身份不过门禁的生成底片；双人段必须 probe-first；源脸=真实照片裁切',
        'limitations': '运行时索引可逐帧漂移（次序翻转窗必须切窗）；小脸/闪光窗 SFace 可能低于清晰线（视觉+单锚补判）；inswapper_128 上限',
        'key_params_json': json.dumps({'node10': 'source face crop (real photo)', 'node11': 'target plate', 'node15_input_faces_index': 'measured at runtime, NOT assumed', 'output_fix': 'setpts=PTS/2,fps=24'}),
        'metrics_json': json.dumps({'S6_photo_moment': {'girl': '0.75-0.81 (project best)', 'hua': 'below clear bar; single-anchor 0.63-0.70; visual real-photo verdict'}, 'S2_dark_spotlight': {'median': 0.722}, 'blind_chain_failure': {'girl': '0.30-0.38 after cross-swap'}}),
        'cost_json': json.dumps({'coins_per_5s': '10-15', 'probe_pass': '+1 repair per window'}),
        'success_cases_json': json.dumps(['concert30 v3.2 合影窗重建：她 0.75-0.81 + 视觉"真实照片"级']),
        'failure_cases_json': json.dumps(['盲跑链修交叉换脸（v3.2 S6v4 首次）', 'S6ab ref01 小脸窗修复未生效']),
        'evidence_note': f'concert30 v3.2；完整叙述见 {DOC} §8.2', 'source': 'agent_composed'})

    conn.commit()
    n1 = conn.execute("SELECT COUNT(*) c FROM expert_solutions").fetchone()['c']
    n2 = conn.execute("SELECT COUNT(*) c FROM boundary_laws").fetchone()['c']
    print(f'totals: solutions={n1} laws={n2}')
    conn.close()

if __name__ == '__main__':
    main()
