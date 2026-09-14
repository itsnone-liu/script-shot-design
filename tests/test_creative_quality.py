from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from shortfilm.creative_quality import (
    validate_beat_design,
    validate_cinematic_scene_design,
    validate_creative_strategy,
    validate_story_design,
)
from stages import messages_for
from shortfilm.prompt_contract import compile_minimax_prompt

ROOT = Path(__file__).resolve().parents[1]


class CreativeQualityTests(unittest.TestCase):
    def setUp(self):
        self.concepts = json.loads((ROOT / "fixtures/concept_candidates.json").read_text(encoding="utf-8"))
        self.story = json.loads((ROOT / "fixtures/story_statement.json").read_text(encoding="utf-8"))
        self.beats = json.loads((ROOT / "fixtures/beat_sheet.json").read_text(encoding="utf-8"))
        self.scenes = json.loads((ROOT / "fixtures/scene_cards.json").read_text(encoding="utf-8"))

    def test_creative_fixture_uses_distinct_engines(self):
        self.assertEqual([], validate_creative_strategy(self.concepts))

    def test_flat_concept_without_expectation_design_blocks(self):
        doc = copy.deepcopy(self.concepts)
        del doc["candidates"][0]["creative_strategy"]["expectation_break"]
        issues = validate_creative_strategy(doc)
        self.assertTrue(any(x["code"] == "missing_creative_strategy_field" for x in issues))

    def test_cosmetic_variations_using_one_engine_block(self):
        doc = copy.deepcopy(self.concepts)
        for candidate in doc["candidates"]:
            candidate["creative_strategy"]["creative_engine"] = "cause_effect_chain"
        issues = validate_creative_strategy(doc)
        self.assertTrue(any(x["code"] == "concepts_not_mechanically_distinct" for x in issues))

    def test_three_turn_escalation_is_required(self):
        doc = copy.deepcopy(self.concepts)
        doc["candidates"][1]["creative_strategy"]["escalation_ladder"] = ["same action again"]
        issues = validate_creative_strategy(doc)
        self.assertTrue(any(x["code"] == "weak_escalation_ladder" for x in issues))

    def test_story_and_beat_design_survive_concept_selection(self):
        self.assertEqual([], validate_story_design(self.story))
        self.assertEqual([], validate_beat_design(self.beats))

    def test_story_without_ending_reframe_blocks(self):
        doc = copy.deepcopy(self.story)
        del doc["ending_reframe"]
        issues = validate_story_design(doc)
        self.assertTrue(any(x["code"] == "missing_story_design_field" for x in issues))

    def test_beat_without_information_change_blocks(self):
        doc = copy.deepcopy(self.beats)
        del doc["beats"][2]["new_information"]
        issues = validate_beat_design(doc)
        self.assertTrue(any(x["code"] == "missing_beat_design_field" for x in issues))

    def test_cinematic_scene_fixture_is_complete(self):
        self.assertEqual([], validate_cinematic_scene_design(self.scenes))

    def test_shot_without_information_job_blocks(self):
        doc = copy.deepcopy(self.scenes)
        del doc["scenes"][0]["shot_list"][0]["cinematic_design"]["audience_knowledge"]
        issues = validate_cinematic_scene_design(doc)
        self.assertTrue(any(x["code"] == "missing_cinematic_design_field" for x in issues))

    def test_more_than_three_concurrent_events_blocks(self):
        doc = copy.deepcopy(self.scenes)
        doc["scenes"][0]["shot_list"][0]["cinematic_design"]["event_budget"]["max_concurrent_events"] = 4
        issues = validate_cinematic_scene_design(doc)
        self.assertTrue(any(x["code"] == "visual_event_overload" for x in issues))

    def test_cinematic_design_reaches_minimax_prompt(self):
        contract = json.loads((ROOT / "examples/script_first/coffee30_story_segA_v1.json").read_text(encoding="utf-8"))
        contract["internal_shots"][0]["cinematic_design"] = {
            "narrative_job": "connect the gift to the sleeping protagonist",
            "audience_knowledge": {"knows": "someone prepared coffee", "does_not_know": "who", "question": "who is caring for her"},
            "composition_logic": "foreground curtain frames the face on the right third",
            "blocking_map": {"subject_position": "face on right third", "movement_path": "light crosses left to right", "camera_position": "bedside at pillow height", "screen_direction": "left to right"},
            "performance_detail": {"micro_action": "one natural breath and a tiny eyelid movement", "reaction_order": "light arrives before eyelid response"},
            "light_motivation": {"source": "upper-left window", "direction": "upper-left to lower-right", "color_temperature": "5600K"},
            "event_budget": {"max_concurrent_events": 2, "timed_events": ["light travel", "eyelid response"]},
        }
        prompt = compile_minimax_prompt(contract)
        self.assertIn("Frame:", prompt)
        self.assertIn("Blocking:", prompt)
        self.assertIn("Performance:", prompt)
        self.assertIn("Light:", prompt)
        self.assertIn("Density: max 2", prompt)
        self.assertNotIn("Audience information:", prompt)
        self.assertIn("EDITING AND PERFORMANCE RULE", prompt)

    def test_five_shot_cinematic_contract_stays_inside_prompt_budget(self):
        for name in ("coffee30_dont_wake_her_segA_v1.json", "coffee30_dont_wake_her_segB_v1.json"):
            contract = json.loads((ROOT / "examples/creative_v2" / name).read_text(encoding="utf-8"))
            contract["user_script_review"] = {"status":"approved", "script_version":"draft", "reviewed_by":"test"}
            prompt = compile_minimax_prompt(contract)
            self.assertLessEqual(len(prompt), 7000)
            self.assertIn("Performance:", prompt)
            self.assertIn("Density: max", prompt)

    def test_stage_prompt_separates_creative_and_cinematic_work(self):
        concept_prompt = messages_for("concept_candidates", {}, {}, {}, [])[1]["content"]
        scene_prompt = messages_for("scene_cards", {}, {}, {}, [])[1]["content"]
        self.assertIn("expectation_break", concept_prompt)
        self.assertIn("cliche_rejected", concept_prompt)
        self.assertIn("cinematic_design", scene_prompt)
        self.assertIn("max_concurrent_events", scene_prompt)
        self.assertIn("audience_knowledge", scene_prompt)


if __name__ == "__main__":
    unittest.main()
