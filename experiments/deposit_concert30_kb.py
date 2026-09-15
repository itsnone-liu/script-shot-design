# -*- coding: utf-8 -*-
"""Deposit concert30 v1-v3 identity-pipeline experience into 820's ComfyUI workflow KB.

Layers written:
  expert_solutions : ref2va_identity_recipe / reactor_role_chain_repair (candidate + evidence)
  boundary_laws    : 6 laws (BL-1xx free slots, checked against existing)
  decision_rules   : 3 rules (DR-1xx free slots)
Idempotent: checks existence before insert. Backs up kb.db first.
Full narrative: 821/knowledge/IDENTITY_HYBRID_PIPELINE_V1.md
"""
from __future__ import annotations
import json, shutil, sqlite3, sys
from datetime import datetime
from pathlib import Path

P820 = Path(r'D:\qjcNetDiskDownload\deepseek-harness\project\820')
DB = P820 / 'data' / 'kb.db'
DOC = '821/knowledge/IDENTITY_HYBRID_PIPELINE_V1.md'

def backup():
    stamp = datetime.now().strftime('%Y%m%d')
    bak = P820 / 'data' / f'kb.db.bak-{stamp}-preConcert30'
    if not bak.exists():
        shutil.copy2(DB, bak)
        print(f'backup -> {bak.name}')
    else:
        print(f'backup exists: {bak.name}')

def next_code(conn, table, prefix):
    row = conn.execute(f"SELECT code FROM {table} WHERE code LIKE '{prefix}%'").fetchall()
    used = {r['code'] for r in row}
    n = 100
    while f'{prefix}-{n}' in used:
        n += 1
    return f'{prefix}-{n}'

def insert_solution(conn):
    name = 'ref2va_identity_recipe'
    if conn.execute("SELECT 1 FROM expert_solutions WHERE name=?", (name,)).fetchone():
        print('solution exists:', name)
    else:
        conn.execute("""INSERT INTO expert_solutions
            (name,status,family,requirements,capabilities_json,route_json,workflow_ref,
             applicable_conditions,limitations,key_params_json,metrics_json,cost_json,
             success_cases_json,failure_cases_json,evidence_note,source)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (name, 'candidate', 'video_identity_gen',
             '真实人物出演AI视频 参考图身份一致 真人长相不变 identity consistency reference',
             json.dumps(['identity_transfer', 'structure_preserve']),
             json.dumps([
                 {'step': 1, 'op': 'build_ref_pack', 'detail': 'YuNet 最大脸 bbox×1.6 确定性裁切做 Picture 1；表情/正面/全身各一，共4图'},
                 {'step': 2, 'op': 'configure', 'detail': 'int8 UNET + SameFace_Fix 0.5 + turbo_6step + ref_image_size=max + 1344x768'},
                 {'step': 3, 'op': 'prompt', 'detail': '参考图职责显式声明 + 硬属性每帧强制 + 单一连续场景 + 首尾正脸锚 + action_mandate + 禁区清单'},
                 {'step': 4, 'op': 'gate', 'detail': 'qa_identity.py 角色窗口 median>=0.60；漂移则转 reactor_role_chain_repair'}]),
             'runninghub:2093518439926218753',
             '有 4+ 张清晰日常照的真人；单一连续场景；4-15s；<=9 参考图',
             '身份-动作交换律：全力冲刺不可得，energetic fast-walk 是天花板（能量靠剪辑 1.6x 提速）；蒙太奇提示必漂移；追光+大表情事件下身份渐进漂移（需修复链兜底）',
             json.dumps({'sameface_fix': 0.5, 'picture_1': 'face_crop_anchor', 'unet': 'int8_convrot', 'steps': 6,
                         'resolution': '1344x768', 'duration_range': '4-15'}),
             json.dumps({'girl_4attempts': {'v1_montage': 0.2652, 'v2_no_crop_anchor': 0.1744, 'v3_energy': 0.60, 'v4_accept': 0.60},
                         'public_figure_pure_gen': {'smoke_median': 0.3482, 'v3_smoke': [0.42, 0.52, 0.15]},
                         'sface_same_person_threshold': 0.363, 'note': '跨输入不可直接比；SFace/YuNet 实测'}),
             json.dumps({'coins_per_5s': 47, 'minutes': '8-10'}),
             json.dumps(['concert30 S3v4 ACCEPT median 0.60 hero 0.7285',
                         'concert30 v3 S2/S3/S4/S5/S6 底片场景全对（修复后全过线）']),
             json.dumps(['蒙太奇→群像漂移 0.2652', '无裁切锚→错人 0.1744', '追光段漂移 0.59→0.18', '纯生成公众人物 FAIL']),
             f'concert30 v1-v3 全程实证；完整叙述见 {DOC}', 'agent_composed'))
        print('solution inserted:', name)

    name = 'reactor_role_chain_repair'
    if conn.execute("SELECT 1 FROM expert_solutions WHERE name=?", (name,)).fetchone():
        print('solution exists:', name)
    else:
        conn.execute("""INSERT INTO expert_solutions
            (name,status,family,requirements,capabilities_json,route_json,workflow_ref,
             applicable_conditions,limitations,key_params_json,metrics_json,cost_json,
             success_cases_json,failure_cases_json,evidence_note,source)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (name, 'candidate', 'face_swap',
             '生成视频换回真人脸 双人同框各自保身份 身份修复 identity repair face swap video',
             json.dumps(['identity_transfer', 'expression_preserve', 'structure_preserve']),
             json.dumps([
                 {'step': 1, 'op': 'role_map', 'detail': 'YuNet top-2 脸 × SFace 对双角色参考逐帧打分，输出 时间→脸索引→角色 表'},
                 {'step': 2, 'op': 'branch', 'detail': '次序稳定→固定索引链修（先修1号再修0号）；次序漂移→按剧情弧线切窗分段修；单人→0号直修'},
                 {'step': 3, 'op': 'run', 'detail': 'node10=真实照片脸裁切(源)，node11=底片，node15 input_faces_index 选脸'},
                 {'step': 4, 'op': 'post', 'detail': 'RIFE 半速输出 → setpts=PTS/2 + fps=24 回速；切窗片段 concat 无痕拼回'}]),
             'runninghub:2005804455352303618',
             '任何身份不过门禁的生成底片；双人段需角色映射先行；源脸必须真实照片裁切',
             '检测次序翻转帧会交叉换脸（必须先做角色映射）；inswapper_128 分辨率上限致剧烈大表情处几何残留；输出半速需回速',
             json.dumps({'node10': 'source face crop (real photo)', 'node11': 'target plate video',
                         'node15_input_faces_index': '0|1 per role map', 'face_restore_visibility': 0.4,
                         'output_fix': 'setpts=PTS/2,fps=24'}),
             json.dumps({'S2_drift_repair': {'before': 0.2525, 'after_median': 0.6616},
                         'S3_crowd': {'before': 0.5294, 'after_median': 0.7523},
                         'S5_two_person': {'girl': '0.71-0.76', 'hua': '0.56-0.69 (median 0.6367)'},
                         'S6_photo': {'girl_median': 0.777, 'peak': 0.811},
                         'dark_scene_discount': '0.10-0.15 vs bright ambient'}),
             json.dumps({'coins_per_5s': '10-15', 'minutes': '4-8'}),
             json.dumps(['concert30 S2/S3/S4/S5/S6 v3 全部过线交付']),
             json.dumps(['固定索引未做角色映射→次序翻转帧交叉换脸风险（S4 实测翻转，改切窗解决）']),
             f'concert30 v3 核心创新；完整叙述见 {DOC}', 'agent_composed'))
        print('solution inserted:', name)

def insert_laws(conn):
    laws = [
        ('Ref2VA身份动作交换律', 'Ref2VA 用身份换动作：身份锁得越死，可演出动作越少，全力冲刺不可得。',
         '参考图身份约束占用生成容量，动作幅度被系统性压缩；实测天花板为 energetic fast-walk。冲刺能量应由剪辑变速（1.6x 实测有效）制造。',
         'concert30 S3 四轮迭代：v3 身份过关(0.60)但动作=快走；v1-v2 动作大但身份崩(0.27/0.17)'),
        ('参考污染律', '海报/合照等含他人脸的原图直接做参考会污染身份嵌入，必须先做确定性人脸裁切。',
         '最大脸嵌入会被图内第二人脸干扰；YuNet bbox×1.5-1.6 外扩裁切是可复现的净化手段（禁手工截）。',
         'concert30 ref06 原图 1/3 参考评测失败；G2 裁切后 4/4 PASS(0.5491-0.5897)'),
        ('暗场嵌入折扣律', '追光+黑暗人群场景的 SFace 余弦系统性低 0.10-0.15，低分可能是度量问题而非身份问题。',
         '强光比+暗部噪声劣化嵌入；实测压光不能恢复分值（0.2525→0.2199 无效）。判定需视觉+真实源+多窗口锚共同定论。',
         'concert30 S2：亮环境修复 0.66-0.77 vs 暗场修复 0.49-0.62，场景内容视觉确认同一人'),
        ('蒙太奇漂移律', 'Ref2VA 多场景/蒙太奇提示会漂成群像/自拍，主角消失。',
         '时序注意力在场景切换处丢失主体锚；单一连续场景是硬约束。',
         'concert30 S3 v1 median 0.2652 女孩消失；改单场景后 v2 起主体稳定'),
        ('水印继承律', 'Ref2VA 会把参考图里的水印/字幕继承进生成画面。',
         '官摄参考图自带平台水印与歌词字幕时，生成帧复现之；用过此类参考的底片需在剪辑做安全裁切。',
         'concert30 S6v3 生成帧出现“华晨宇工作室|bilibili”水印+歌词条；剪辑 crop 顶部40px+字幕后消除'),
        ('联系表低报律', '缩略联系表会系统性低报关键动作帧与细节，不能作为关键剧情点的最终判据。',
         '480px 拼图丢失手部接触/微表情分辨率；全分辨率抽帧验证是关键帧判定的必要步骤。',
         'concert30 v3 母版联系表称“拉上台无接触”，全分辨率 16.3s 帧确认握腕上拉清晰成立'),
    ]
    code_by_name = {}
    for name, statement, technical, evidence in laws:
        if conn.execute("SELECT 1 FROM boundary_laws WHERE name=?", (name,)).fetchone():
            print('law exists:', name); continue
        code = next_code(conn, 'boundary_laws', 'BL')
        conn.execute("INSERT INTO boundary_laws (code,name,statement,technical,evidence,status,attribution) VALUES (?,?,?,?,?,'law',?)",
                     (code, name, statement, technical, evidence, 'concert30 v1-v3 实证 (821)'))
        code_by_name[name] = code
        print('law inserted:', code, name)
    return code_by_name

def insert_rules(conn, codes):
    # find solution ids for routes
    ids = {r['name']: r['id'] for r in conn.execute("SELECT id,name FROM expert_solutions").fetchall()}
    rules = [
        ('真实人物出镜视频 → 生成场景+ReActor修复',
         json.dumps([{'facet': 'task', 'op': 'is', 'val': 'real_person_video'},
                     {'facet': 'identity', 'val': 'strict'}]),
         'reactor_role_chain_repair', '生成负责场景光影，修复负责真人脸',
         '身份=真实照片几何，全片光影统一在生成域；纯生成公众人物不可交付(0.35-0.52)',
         '修复链检测次序翻转会交叉换脸，先做角色映射',
         '任何真人身份要求严格且剧情含真实素材拍不出的互动', '~60币/5s(生成47+修复15)', 'recommended',
         json.dumps([codes['Ref2VA身份动作交换律'], codes['参考污染律']]), ''),
        ('双人同框身份 → 角色映射链式修复',
         json.dumps([{'facet': 'faces', 'op': 'is', 'val': 'two_person'},
                     {'facet': 'identity', 'val': 'both_roles'}]),
         'reactor_role_chain_repair', '逐帧角色映射后按索引链修或按剧情切窗分段修',
         '同框双人各自过线（实测 0.71-0.76 / 0.56-0.69）；同源素材拼回无痕',
         '次序不稳定时固定索引必交叉换脸；须切窗',
         '两人都要清晰身份的互动镜头（拉手/合影）', '~25币/5s(两次修复)', 'recommended',
         json.dumps([codes['蒙太奇漂移律']]), ''),
        ('纯 Ref2VA 生成公众人物 → 不可交付',
         json.dumps([{'facet': 'task', 'op': 'is', 'val': 'public_figure_pure_gen'}]),
         '', '直接用参考图生成公众人物身份',
         '气质造型可对但 SFace 不过线（0.3482 / 0.42-0.52 vs 0.60）',
         '视觉会说 PASS——公众人物身份必须 SFace 量化，禁视觉单判',
         '仅冒烟测场景可行性时用；正式素材走生成+修复', '~47币', 'dead',
         json.dumps([codes['参考污染律']]), 'concert30 S1 冒烟 median 0.3482 REJECT；v3 冒烟 0.42-0.52'),
    ]
    for name, conditions, route, what, effect, risk, when_choose, coins, tone, laws, dead_ref in rules:
        if conn.execute("SELECT 1 FROM decision_rules WHERE name=?", (name,)).fetchone():
            print('rule exists:', name); continue
        code = next_code(conn, 'decision_rules', 'DR')
        conn.execute("""INSERT INTO decision_rules
            (code,name,conditions_json,route,route_label,what,effect_cost,risk,when_choose,coins,tone,dead_ref,laws_json,source_kind,attribution,evidence)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (code, name, conditions, route, what, what, effect, risk, when_choose, coins, tone, dead_ref, laws,
             'experiment', 'concert30 v1-v3 实证 (821)', f'详见 {DOC}'))
        print('rule inserted:', code, name)

def main():
    if not DB.exists():
        sys.exit(f'missing {DB}')
    backup()
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('SELECT 1 FROM boundary_laws LIMIT 1'); conn.execute('SELECT 1 FROM expert_solutions LIMIT 1')
    except sqlite3.OperationalError as e:
        sys.exit(f'schema missing ({e}); run migrations first')
    codes = insert_laws(conn); insert_solution(conn); insert_rules(conn, codes)
    conn.commit()
    n1 = conn.execute('SELECT COUNT(*) c FROM expert_solutions').fetchone()['c']
    n2 = conn.execute('SELECT COUNT(*) c FROM boundary_laws').fetchone()['c']
    n3 = conn.execute('SELECT COUNT(*) c FROM decision_rules').fetchone()['c']
    print(f'totals: solutions={n1} laws={n2} rules={n3}')
    conn.close()

if __name__ == '__main__':
    main()
