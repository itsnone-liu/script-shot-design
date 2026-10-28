"""Make a filename-blinded review bundle and a SEPARATE operator mapping.

No claim of perfect blinding: visual content, duration and embedded metadata
may still reveal provenance. Inspect/remux media before real review. Never
ship the private mapping directory to reviewers. Refuses existing bundles.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import random
import secrets
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/creative_v2/coffee30_v2_unsent'
MANIFEST=OUT/'asset_manifest.json'
AXES=[('emotion_turn','情绪转折可读性'),('reveal_clarity','注意力揭示清晰度'),('action_physics','动作物理可信'),('continuity','镜间连续性'),('rhythm','节奏与长短对比'),('overall','整体完成度')]


def build_bundle(manifest_path:Path, public:Path, private:Path, seed:int)->dict:
    if public.resolve()==private.resolve() or public.resolve() in private.resolve().parents or private.resolve() in public.resolve().parents:
        raise ValueError('public and private directories must be separate siblings or independent paths')
    if public.exists() or private.exists():
        raise ValueError('refuse overwrite: choose fresh public and private directories')
    doc=json.loads(manifest_path.read_text(encoding='utf-8'))
    takes=[t for t in doc.get('takes',[]) if t.get('status')=='success' and t.get('outputs')]
    if not takes:raise ValueError('no successful media to review')
    ids=[t['shot_id'] for t in takes]
    if len(ids)!=len(set(ids)):raise ValueError('duplicate shot_id')
    rng=random.Random(seed);rng.shuffle(takes)
    sources=[]
    for take in takes:
        source=Path(take['outputs'][0])
        if not source.is_absolute():source=manifest_path.parent/source
        if not source.is_file():raise FileNotFoundError(source)
        sources.append(source)
    public.mkdir(parents=True);private.mkdir(parents=True)
    lines=['# 匿名候选评分表','', '每轴1–5分；无法评价填N/A。仅看匿名文件，不接触来源映射。', '', '文件名匿名不等于完全盲法；画面/时长/媒体元数据仍可能提供线索。','']
    lines += [f'- {code}：{title}' for code,title in AXES]
    lines += ['', '| 盲码 | 文件 | '+' | '.join(c for c,_ in AXES)+' |','|'+'---|'*(len(AXES)+2)]
    mapping=[]
    for index,(take,source) in enumerate(zip(takes,sources),1):
        code=f'V{index:03d}';filename=code+source.suffix.lower();dest=public/filename
        shutil.copyfile(source,dest)
        digest=hashlib.sha256(dest.read_bytes()).hexdigest()
        mapping.append({'blind_code':code,'file':filename,'sha256':digest,'source':str(source),'take':take})
        lines.append(f'| {code} | {filename} | '+' | '.join(' ' for _ in AXES)+' |')
    (public/'review.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (private/'mapping.json').write_text(json.dumps({'seed':seed,'entries':mapping},ensure_ascii=False,indent=2),encoding='utf-8')
    return {'count':len(mapping),'public':str(public),'private':str(private),'scope':'filename blinding only; metadata/content require review'}


def main(argv=None)->int:
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,default=MANIFEST);p.add_argument('--public',type=Path,default=OUT/'review_public');p.add_argument('--private',type=Path,default=OUT/'review_private');p.add_argument('--seed',type=int)
    a=p.parse_args(argv)
    try:
        report=build_bundle(a.manifest,a.public,a.private,a.seed if a.seed is not None else secrets.randbits(64))
    except (ValueError,FileNotFoundError) as ex:
        print('REFUSED:',ex);return 3
    print(json.dumps(report,ensure_ascii=False));return 0

if __name__=='__main__':raise SystemExit(main())
