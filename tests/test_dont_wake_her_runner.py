from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_dont_wake_her", ROOT / "experiments/run_coffee30_dont_wake_her.py"
)
RUNNER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(RUNNER)


class DontWakeHerRunnerTests(unittest.TestCase):
    def documents(self):
        return [RUNNER.load_json(spec["contract"]) for spec in RUNNER.SEGMENTS.values()]

    def test_pending_contracts_are_refused(self):
        docs = self.documents()
        for doc in docs:
            doc["user_script_review"] = {"status": "pending", "script_version": RUNNER.VERSION, "reviewed_by": ""}
        errors = RUNNER.approval_errors(docs)
        self.assertTrue(errors)
        self.assertTrue(all("approval" in x or "reviewed_by" in x for x in errors))

    def test_both_contracts_require_exact_same_approved_version(self):
        docs = self.documents()
        for doc in docs:
            doc["user_script_review"] = {
                "status": "approved", "script_version": RUNNER.VERSION, "reviewed_by": "user"
            }
        self.assertEqual([], RUNNER.approval_errors(docs))
        docs[1]["user_script_review"]["script_version"] = "stale-version"
        self.assertTrue(any("script_version" in x for x in RUNNER.approval_errors(docs)))

    def test_preflight_compiles_without_rendering(self):
        docs = self.documents()
        prompts = RUNNER.compile_draft_prompts(docs)
        self.assertEqual({"A", "B"}, set(prompts))
        self.assertTrue(all(len(prompt) <= 7000 for prompt in prompts.values()))

    def test_approval_check_does_not_call_renderer(self):
        docs = self.documents()
        for doc in docs:
            doc["user_script_review"] = {"status": "pending", "script_version": RUNNER.VERSION, "reviewed_by": ""}
        with patch.object(RUNNER, "render_packet") as render:
            self.assertTrue(RUNNER.approval_errors(docs))
            render.assert_not_called()

    def test_production_plan_matches_runner_take_budget(self):
        plan = json.loads(RUNNER.PLAN_PATH.read_text(encoding="utf-8"))
        self.assertEqual(3, RUNNER.SEGMENTS["A"]["planned_takes"])
        self.assertEqual(4, RUNNER.SEGMENTS["B"]["planned_takes"])
        self.assertEqual(
            sum(spec["planned_takes"] for spec in RUNNER.SEGMENTS.values()),
            plan["container_budget"]["estimated_paid_calls_after_approval"],
        )

    def test_every_keyframe_has_continuity_and_qa(self):
        plan = json.loads(RUNNER.PLAN_PATH.read_text(encoding="utf-8"))
        frames = plan["reference_strategy"]["required_keyframes"]
        self.assertEqual(4, len(frames))
        for frame in frames:
            self.assertTrue(frame["description"])
            self.assertGreaterEqual(len(frame["continuity_lock"]), 4)
            self.assertGreaterEqual(len(frame["qa"]), 4)


if __name__ == "__main__":
    unittest.main()
