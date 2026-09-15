# -*- coding: utf-8 -*-
"""Deposit concert30 v3.3 laws into 820's ComfyUI workflow KB (idempotent, backs up first)."""
from __future__ import annotations
import os, shutil, sqlite3
from datetime import datetime

P820 = r'D:\qjcNetDiskDownload\deepseek-harness\project\820'
DB = os.path.join(P820, 'data', 'kb.db')

def main():
    bak = os.path.join(P820, 'data', 'kb.db.bak-20260915-preConcert30v33')
    if not os.path.exists(bak):
        shutil.copy2(DB, bak); print('backup ok')
    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row

    laws = [
        ('帧级索引漂移律', '修复器的人脸序号逐帧漂移；双人窗修复的充分验证只有逐帧双角色扫描，抽样+抽帧目检会漏检。',
         '序号由检测器逐帧重排决定；任何静态索引方案在长窗必然错帧。验证=每帧每脸对双角色参考组打分、逐帧角色归位。',
         'concert30 v3.2 合影窗：6 帧抽样全绿但用户实看 25-27s 交叉换脸；v3.3 逐帧扫描复现'),
        ('性别定向失效律', 'detect_gender_input 定向修复对浓舞台妆男性失效（被性别分类器判为女性）。',
         '性别分类器对红唇/细眉/亮片装男妆判女；女刀打错+男刀无目标。适用条件=素颜/淡妆日常着装。',
         'concert30 S6v5：male 刀无效果、female 刀仍打他；换位置分割后根治'),
        ('位置分割修复律', '双人位置全程不交叉时，沿边界切半幅各自修复（单脸=序号恒0），拼回即根治交叉。',
         '先用检测器逐帧打印脸盒 x 区间确认不交叉；边界取两人脸盒相邻处；亮场素材拼缝需羽化，暗场/闪光灯画面硬拼即可。',
         'concert30 v3.3：边界 x=633/634 切分，逐帧她 0.75-0.82/他 0.58-0.66，拼缝不可见'),
    ]
    for name, st, tech, ev in laws:
        if conn.execute('SELECT 1 FROM boundary_laws WHERE name=?', (name,)).fetchone():
            print('exists', name); continue
        used = {r[0] for r in conn.execute("SELECT code FROM boundary_laws WHERE code LIKE 'BL-%'")}
        n = 100
        while f'BL-{n}' in used: n += 1
        conn.execute("INSERT INTO boundary_laws (code,name,statement,technical,evidence,status,attribution) VALUES (?,?,?,?,?,'law',?)",
                     (f'BL-{n}', name, st, tech, ev, 'concert30 v3.3 实证 (821)'))
        print('inserted', f'BL-{n}', name)

    r = conn.execute("SELECT id FROM expert_solutions WHERE name='reactor_role_chain_repair' ORDER BY version DESC LIMIT 1").fetchone()
    rid = r['id']
    conn.execute("UPDATE expert_solutions SET limitations = limitations || ?, evidence_note = evidence_note || ?, updated_at = datetime('now') WHERE id = ?",
                 ('；浓妆男性性别定向失效；双人长窗必须逐帧双角色验证，位置不交叉时优先位置分割修复（v3.3）',
                  ' + v3.3 位置分割根治', rid))
    print('solution updated id', rid)
    conn.commit(); conn.close()

if __name__ == '__main__':
    main()
