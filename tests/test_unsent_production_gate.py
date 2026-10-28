"""Fail-closed production and endpoint checks; no API calls."""
import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from experiments import run_coffee30_v2_unsent as runner

class ProductionGateTest(unittest.TestCase):
    def test_current_design_and_production_are_not_approved(self):
        errors=runner.production_errors()
        self.assertTrue(any('design package' in e for e in errors))
        self.assertTrue(any('production plan' in e for e in errors))

    def test_endpoint_keyframe_is_gated_separately(self):
        with patch.object(runner.REGISTRY_PATH.__class__, 'exists', return_value=True), patch.object(runner,'load_registry',return_value={'keyframes':{}}), patch.object(runner,'gate_errors',return_value=[]) as gate:
            runner.registry_errors({'A':{'internal_shots':[]}})
        self.assertEqual(gate.call_count,2)
        self.assertEqual(gate.call_args_list[-1].args[0]['internal_shots'][0]['first_frame']['keyframe_id'],'KF_V2_A_LAST')

    def test_unchecked_template_refuses(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'check.json'
            path.write_text(json.dumps({'entries':[{'keyframe_id':'KF','items':{}}]}),encoding='utf-8')
            with patch.object(runner,'CHECKLIST_PATH',path):
                errors = runner.checklist_errors()
                self.assertEqual(sum("not checked" in e for e in errors),5)
                self.assertTrue(any("missing required keyframes" in e for e in errors))

if __name__=='__main__':unittest.main()
