"""Second-pass editor for product visual concepts that fail the product gate."""
from __future__ import annotations
import argparse,json,os,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from llm.openai_compat import OpenAICompatibleClient
from validators import validate_visual_design,status

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',required=True); ap.add_argument('--brief',required=True); ap.add_argument('--out',required=True); ap.add_argument('--timeout',type=int,default=300); a=ap.parse_args()
    old=json.loads(Path(a.input).read_text(encoding='utf-8')); brief=json.loads(Path(a.brief).read_text(encoding='utf-8')); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    task={
      'role':'product visual design director and hostile production reviewer',
      'instruction':'You are both a hostile reviewer and a replacement designer. First reject bad candidates internally, then MUST invent at least five replacement concepts and return them. Never return an empty concepts list, null script, or only a rejection report. Do not patch the old visual language. The replacements must be concrete product-material transformations, not abstract design explanations.',
      'brief':brief,
      'candidate_package':{'do_not_reuse':old.get('concepts',[]),'rejection_reason':'Previous package is reference for failure analysis only; invent new visual mechanisms.'},
      'hard_quality_rules':[
        'A deliverable visual transformation must use a recognizable physical substance: whole coffee bean, crushed coffee, water, liquid coffee, ice, condensation, glass bottle, foam, or another explicit coffee material.',
        'Each transition must be written as BEFORE MATERIAL + PHYSICAL ACTION + INTERMEDIATE STATE + AFTER MATERIAL. If any term is missing, reject it.',
        'The product cannot become a generic shape. It must remain identifiable as bean, coffee liquid, ice, condensation, glass, or finished bottle.',
        'A negative phrase such as no blocks is not a design. Replace the bad abstraction with a concrete material action.',
        'Each segment is exactly 15 seconds and has one continuous camera move; the 30-second film is two segments edited together.',
        'The prompt must be directly executable by MiniMax, with one main subject, four timed actions, camera path, first frame, last frame, and never-show list.',
        'Reject concepts that need readable text, invisible sound, unexplained magic, ice flowers, decorative patterns, abstract ribbons, generic particles, or simultaneous multi-object metamorphosis. Do not reuse any candidate name, transformation_chain, or timeline from the candidate package.'
      ],
      'return_contract':{
        'concepts':'array of exactly 5 objects with id, name, product_property, transformation_chain, physical_causality, anti_block_design, minimax_visual_fit, risk_flags',
        'selected_concept':'object with id, name, reason; id must equal one returned concept',
        'script':'object with exactly part1 and part2; each part has title, duration_sec=15, timeline_0_3, timeline_3_7, timeline_7_11, timeline_11_15, camera_path, first_frame, last_frame, transition_to_next',
        'prompts':'object with exactly part1 and part2; each value is a string containing 总时长, 时间线, 镜头路径, 首帧, 尾帧, 禁止',
        'edit_plan':'object with assembly, transition, sound_design, branding',
        'design_rejection_log':'array of rejected ideas and reasons'
      }
    }
    c=OpenAICompatibleClient(os.environ['EIGHT21_LLM_URL'],os.environ['EIGHT21_LLM_API_KEY'],os.environ['EIGHT21_LLM_MODEL'],timeout=a.timeout)
    result=c.complete([{'role':'system','content':'You are a strict commercial visual director. Product-grade visual design only. Return JSON only.'},{'role':'user','content':json.dumps(task,ensure_ascii=False)}],{'type':'object'},stage='visual-contract-revision')
    issues=validate_visual_design(result); result['_meta']={'source':'visual_contract_revision','visual_gate':status(issues),'visual_issues':issues}
    (out/'visual_concepts_and_script.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':status(issues),'issues':issues,'meta':result['_meta']},ensure_ascii=False,indent=2)); return 1 if status(issues)=='block' else 0
if __name__=='__main__': raise SystemExit(main())
