from __future__ import annotations
import copy, json, tempfile, unittest
from pathlib import Path
from shortfilm.prompt_contract import compile_minimax_prompt, validate_director_contract
from shortfilm.camera_lint import lint_camera
from shortfilm.rh_adapter import build_node_info

ROOT=Path(__file__).resolve().parents[1]

class PromptContractTests(unittest.TestCase):
    def setUp(self):
        self.doc=json.loads((ROOT/'examples/director_contract/coffee_camera_v1.json').read_text(encoding='utf-8'))

    def test_valid_contract_compiles_required_sections(self):
        self.assertEqual([],validate_director_contract(self.doc))
        prompt=compile_minimax_prompt(self.doc)
        for section in ('MAIN VISUAL TASK','PROMPT BIBLE / CONTINUITY LOCK','INTERNAL SHOT TIMELINE','CAMERA PATH','FIRST FRAME','LAST FRAME','FINAL 1 SECONDS HOLD','NEVER SHOW'):
            self.assertIn(section,prompt)

    def test_unapproved_script_blocks(self):
        doc=copy.deepcopy(self.doc); doc['user_script_review']={'status':'pending'}
        self.assertTrue(any('approval' in x for x in validate_director_contract(doc)))

    def test_timeline_gap_blocks(self):
        doc=copy.deepcopy(self.doc); doc['timeline'][1]['start']=3.5
        self.assertTrue(any('must start' in x for x in validate_director_contract(doc)))

    def test_too_many_camera_path_changes_blocks(self):
        doc=copy.deepcopy(self.doc); doc['camera_plan']['path_changes']=2
        self.assertTrue(any('path change' in x for x in validate_director_contract(doc)))

    def test_valid_camera_plan_has_no_errors(self):
        self.assertFalse([x for x in lint_camera(self.doc) if x.severity=='error'])

    def test_static_camera_conflict_blocks(self):
        doc=copy.deepcopy(self.doc); doc['camera_plan']['primary_move']='static'
        self.assertTrue(any(x.rule=='CAM03' for x in lint_camera(doc)))

    def test_duration_budget_blocks(self):
        doc=copy.deepcopy(self.doc); doc['duration']=16; doc['timeline'][-1]['end']=16
        self.assertTrue(any('duration' in x for x in validate_director_contract(doc)))

    def test_prompt_character_budget_blocks(self):
        doc=copy.deepcopy(self.doc); doc['main_visual_task']='x'*7100
        with self.assertRaisesRegex(ValueError,'7000'):
            compile_minimax_prompt(doc)

    def test_t2v_card_rejects_more_than_ten_seconds(self):
        with self.assertRaisesRegex(ValueError,'10'):
            build_node_info({'duration':15,'prompt':'test'},workflow='t2v')

    def test_i2v_card_allows_fifteen_seconds_with_reference(self):
        nodes=build_node_info({'duration':15,'prompt':'test'},workflow='i2v',reference_file='input.png')
        self.assertTrue(any(x['nodeId']=='135' and x['fieldValue']=='15' for x in nodes))

if __name__=='__main__': unittest.main()
