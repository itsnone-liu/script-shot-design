"""Generate a fresh product-visual ad from product properties, not the old script."""
from __future__ import annotations
import argparse,json,os,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from llm.openai_compat import OpenAICompatibleClient
from validators import validate_visual_design, status

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--brief',required=True); ap.add_argument('--reference',required=True); ap.add_argument('--out',required=True); ap.add_argument('--timeout',type=int,default=240); args=ap.parse_args()
    brief=load(args.brief); reference=load(args.reference); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    prompt={
      'task':'从零创作一个30秒无人物、无对白的咖啡产品视觉广告。严禁继承或改写任何旧的设计师/办公桌/截止时间/最后一页剧本。',
      'creative_brief':brief,'reference_patterns':reference,
      'design_principles':[
        '先从咖啡豆、研磨、粉末吸水、液体萃取、油脂、冰、冷凝水、深色液体、香气和容器形态中选择真正的产品特性，不要先套故事模板',
        '30秒由两个约15秒长镜头段落组成；每个段落内部是一镜到底，模型一次完成；两个段落之间用明确的首尾状态匹配衔接',
        '每个15秒段落必须列出0-3秒、3-7秒、7-11秒、11-15秒的连续动作；每一步必须有物理因果和单一主体',
        '允许超现实但必须基于可理解的物理转化；禁止随机方块、无意义粒子、泛泛的高级感、瞬间跳变；不得只用“不要方块”解决问题，必须用具体材质和动作替代它',
        '像草莓入水和草莓变成饮料那样，让观众看见一种东西连续变成另一种东西；咖啡成品必须是转化链的结果，不是突然插入的产品静物；每个转化必须写清楚原材质、施加的物理动作、中间状态和最终材质，不能用“简单图形/抽象形态”占位',
        'MiniMax提示词必须写成可执行的动作时间线、镜头路径、主体锁定、变换顺序、禁止项、首帧和尾帧；不要只写形容词',
        '品牌文字和Logo后期添加，画面中不生成可读文字'
      ],
      'return_contract':{
        'concepts':'至少5个完全不同的产品视觉方案，每个含product_property, transformation_chain, physical_causality, anti_block_design, minimax_visual_fit, risk_flags',
        'selected_concept':'从5个中选1个并说明选择理由',
        'script':'两个15秒段落，每段含timeline_0_3, timeline_3_7, timeline_7_11, timeline_11_15, camera_path, first_frame, last_frame, transition_to_next',
        'prompts':'每段一个可直接给MiniMax的中文长镜头提示词，包含内部时间线和never show列表',
        'edit_plan':'30秒拼接、声音和后期品牌收束'
      }
    }
    c=OpenAICompatibleClient(os.environ['EIGHT21_LLM_URL'],os.environ['EIGHT21_LLM_API_KEY'],os.environ['EIGHT21_LLM_MODEL'],timeout=args.timeout)
    t=time.time(); result=c.complete([{'role':'system','content':'你是产品视觉广告导演和MiniMax长镜头提示词专家。只返回合法JSON，不要输出思考过程。'},{'role':'user','content':json.dumps(prompt,ensure_ascii=False)}],{'type':'object'},stage='visual-reset')
    visual_issues=validate_visual_design(result)
    result['_meta']={'elapsed_sec':round(time.time()-t,2),'source':'fresh_visual_reset','old_script_used':False,'duration_strategy':'2x15s','visual_gate':status(visual_issues),'visual_issues':visual_issues}
    (out/'visual_concepts_and_script.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':status(visual_issues),'issues':visual_issues,'meta':result['_meta']},ensure_ascii=False,indent=2))
    return 1 if status(visual_issues)=='block' else 0
if __name__=='__main__': raise SystemExit(main())
