"""Tests for shot extension consumption (cast/scene_ref/dialogue/first_frame),
prompt_bible drift detection, and the first-frame pay-gate.

Fixture strategy: extend the real couple30_segA_v1 document in memory — its
prompt_bible is card-synthesizable zero-diff (see test_assets), so a valid
asset_refs block can be attached without touching the committed file.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shortfilm.assets import load_asset_cards  # noqa: E402
from shortfilm.camera_lint import lint_camera  # noqa: E402
from shortfilm.keyframe_gate import gate_errors  # noqa: E402
from shortfilm.prompt_contract import compile_minimax_prompt, validate_director_contract  # noqa: E402
from shortfilm.shot_extensions import validate_shot_extensions  # noqa: E402

CARDS_PATH = ROOT / "examples" / "creative_v2" / "asset_cards_couple30_v1.json"
SEGA_PATH = ROOT / "examples" / "creative_v2" / "couple30_segA_v1.json"
STAGING_PATH = ROOT / "examples" / "creative_v2" / "couple30_segA_staging_v1.json"


def base_document() -> dict:
    doc = json.loads(SEGA_PATH.read_text(encoding="utf-8"))
    doc["asset_refs"] = {
        "cards_path": str(CARDS_PATH),
        "cast": ["char_woman", "char_man"],
        "scene_ref": "scene_bedroom",
    }
    doc["staging"] = json.loads(STAGING_PATH.read_text(encoding="utf-8"))
    for shot in doc["internal_shots"]:
        shot["cast"] = ["char_woman", "char_man"]
        shot["scene_ref"] = "scene_bedroom"
        shot["first_frame"] = {
            "keyframe_id": f"KF_{shot['shot_id']}",
            "approval": "approved",
            "continuity_from": "opening" if shot is doc["internal_shots"][0] else doc["internal_shots"][0]["shot_id"],
        }
    return doc


class ShotExtensionValidationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cards = load_asset_cards(CARDS_PATH)

    def test_valid_extensions_pass(self):
        doc = base_document()
        self.assertEqual([], validate_shot_extensions(doc, cards=self.cards))
        self.assertEqual([], validate_director_contract(doc, cards=self.cards))

    def test_off_seg_cast_blocked(self):
        doc = base_document()
        doc["internal_shots"][0]["cast"] = ["char_woman", "char_man", "char_ghost"]
        errors = validate_shot_extensions(doc, cards=self.cards)
        self.assertTrue(any("char_ghost" in e for e in errors), errors)

    def test_cross_scene_shot_blocked(self):
        doc = base_document()
        doc["internal_shots"][1]["scene_ref"] = "scene_kitchen"
        errors = validate_shot_extensions(doc, cards=self.cards)
        self.assertTrue(any("scene_ref" in e and "scene_kitchen" in e for e in errors), errors)

    def test_dialogue_speaker_must_be_in_cast(self):
        doc = base_document()
        doc["internal_shots"][0]["dialogue"] = {"speaker": "scene_bedroom", "line": "起床啦"}
        errors = validate_shot_extensions(doc, cards=self.cards)
        self.assertTrue(any("dialogue.speaker" in e for e in errors), errors)

    def test_valid_dialogue_compiles_into_prompt(self):
        doc = base_document()
        doc["internal_shots"][0]["dialogue"] = {"speaker": "char_woman", "line": "起床啦，再不起来早饭凉了"}
        prompt = compile_minimax_prompt(doc, cards=self.cards)
        self.assertIn('"起床啦，再不起来早饭凉了"', prompt)
        self.assertIn("char_woman says:", prompt)

    def test_prompt_bible_drift_blocked(self):
        doc = base_document()
        doc["prompt_bible"]["palette_lock"] = "hand-edited palette that no longer matches the scene card"
        errors = validate_director_contract(doc, cards=self.cards)
        self.assertTrue(any("palette_lock" in e and "differs from scene card source" in e for e in errors), errors)

    def test_first_frame_structure(self):
        doc = base_document()
        doc["internal_shots"][2]["first_frame"] = {"keyframe_id": "KF_X", "approval": "maybe"}
        errors = validate_shot_extensions(doc, cards=self.cards)
        self.assertTrue(any("first_frame.approval" in e for e in errors), errors)
        doc["internal_shots"][2]["first_frame"] = {
            "keyframe_id": "KF_X",
            "approval": "approved",
            "continuity_from": doc["internal_shots"][3]["shot_id"],  # future shot
        }
        errors = validate_shot_extensions(doc, cards=self.cards)
        self.assertTrue(any("continuity_from" in e for e in errors), errors)

    def test_emotion_requires_trigger(self):
        doc = base_document()
        perf = doc["internal_shots"][0].setdefault("cinematic_design", {}).setdefault("performance_detail", {})
        perf["emotion"] = "委屈"
        errors = validate_director_contract(doc, cards=self.cards)
        self.assertTrue(any("emotion requires" in e and "trigger" in e for e in errors), errors)

    def test_emotion_with_trigger_compiles_into_performance_line(self):
        doc = base_document()
        perf = doc["internal_shots"][0].setdefault("cinematic_design", {}).setdefault("performance_detail", {})
        perf["emotion"] = "被击中的暖"
        perf["trigger"] = "指尖碰到温热的杯壁"
        prompt = compile_minimax_prompt(doc, cards=self.cards)
        self.assertIn("emotion=被击中的暖 triggered by: 指尖碰到温热的杯壁", prompt)

    def test_legacy_segs_unchanged_without_extensions(self):
        for name in ("coffee30_dont_wake_her_segA_v1.json", "coffee30_dont_wake_her_segB_v1.json", "couple30_segA_v1.json"):
            doc = json.loads((ROOT / "examples" / "creative_v2" / name).read_text(encoding="utf-8"))
            self.assertEqual([], validate_director_contract(doc), name)
            self.assertEqual([], [f for f in lint_camera(doc) if f.severity == "error"], name)


class KeyframeGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cards = load_asset_cards(CARDS_PATH)

    def _registry(self, tmp: Path, tamper: bool = False, approval: str = "approved") -> tuple[dict, Path]:
        doc = base_document()
        keyframe = doc["internal_shots"][0]["first_frame"]["keyframe_id"]
        payload = b"fake-keyframe-png-bytes"
        file = tmp / f"{keyframe}.png"
        file.write_bytes(payload)
        if tamper:
            file.write_bytes(payload + b"-edited")
        registry = {
            "schema_version": "keyframe-registry-v1",
            "keyframes": {
                keyframe: {
                    "file": file.name,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "approval": approval,
                    "approved_by": "user",
                    "approved_at": "2026-10-28T00:00:00+08:00",
                }
            },
        }
        registry["keyframes"][keyframe]["file"] = str(file)
        return registry, tmp

    def test_gate_passes_when_approved_and_unchanged(self):
        doc = base_document()
        with tempfile.TemporaryDirectory() as tmp_dir:
            registry, _ = self._registry(Path(tmp_dir))
            gate = gate_errors(doc, registry)
            # only the registered shot can pass; the others are unregistered -> expected errors
            self.assertTrue(all("not found in registry" in e for e in gate), gate)

    def test_gate_blocks_pending_approval(self):
        doc = base_document()
        doc["internal_shots"][0]["first_frame"]["approval"] = "pending"
        gate = gate_errors(doc, {"keyframes": {}})
        self.assertTrue(any("user approval required" in e for e in gate), gate)

    def test_gate_blocks_hash_drift(self):
        doc = base_document()
        with tempfile.TemporaryDirectory() as tmp_dir:
            registry, _ = self._registry(Path(tmp_dir), tamper=True)
            gate = gate_errors(doc, registry)
            self.assertTrue(any("content changed since approval" in e for e in gate), gate)

    def test_gate_blocks_registry_not_yet_approved(self):
        doc = base_document()
        with tempfile.TemporaryDirectory() as tmp_dir:
            registry, _ = self._registry(Path(tmp_dir), approval="pending")
            gate = gate_errors(doc, registry)
            self.assertTrue(any("registry says" in e for e in gate), gate)

    def test_gate_requires_first_frame_by_default(self):
        doc = base_document()
        del doc["internal_shots"][0]["first_frame"]
        gate = gate_errors(doc, {"keyframes": {}})
        self.assertTrue(any("no first_frame" in e for e in gate), gate)
        relaxed = gate_errors(doc, {"keyframes": {}}, require_first_frame=False)
        self.assertEqual([], [e for e in relaxed if "no first_frame" in e])


if __name__ == "__main__":
    unittest.main()
