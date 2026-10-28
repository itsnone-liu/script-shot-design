"""Regression tests for shortfilm.assets (card -> prompt_bible synthesis).

Zero-diff baseline: couple30_segA_v1.json — environment/lighting/palette locks
and subject_lock must synthesize byte-for-byte from the cards + staging file
(ASSET_STORYBOARD_SCHEMA_V1 §5 migration rule).

Run from repo root:  python -m unittest discover -s tests
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shortfilm.assets import (  # noqa: E402
    build_refs_manifest,
    crosscheck_bible,
    load_asset_cards,
    load_cards_files,
    rule_to_never,
    synth_prompt_bible,
)

CARDS = ROOT / "examples" / "creative_v2" / "asset_cards_couple30_v1.json"
CARDS_V2_PROPS = ROOT / "examples" / "creative_v2" / "asset_cards_coffee30_v2_props.json"
SEGA = ROOT / "examples" / "creative_v2" / "couple30_segA_v1.json"
STAGING = ROOT / "examples" / "creative_v2" / "couple30_segA_staging_v1.json"
IDENTITY = ROOT / "examples" / "couple30_v1" / "identity"

CAST = ["char_woman", "char_man"]
SCENE = "scene_bedroom"


class SynthesisTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cards = load_asset_cards(CARDS)
        cls.staging = json.loads(STAGING.read_text(encoding="utf-8"))
        cls.seg = json.loads(SEGA.read_text(encoding="utf-8"))
        cls.bible = synth_prompt_bible(cls.cards, CAST, SCENE, cls.staging)

    def test_scene_locks_zero_diff(self):
        hand = self.seg["prompt_bible"]
        for field in ("environment_lock", "lighting_lock", "palette_lock"):
            self.assertEqual(hand[field], self.bible[field], f"{field} must be zero-diff")

    def test_subject_lock_zero_diff(self):
        self.assertEqual(self.seg["prompt_bible"]["subject_lock"], self.bible["subject_lock"])

    def test_material_fragments_set_equal_with_staging_suffix(self):
        hand = self.seg["prompt_bible"]["material_lock"]
        hand_fragments = {x.strip().lower() for x in hand.split(";")[0].split(",")}
        syn_fragments = {x.strip().lower() for x in self.bible["material_lock"].split(";")[0].split(",")}
        self.assertEqual(hand_fragments, syn_fragments)
        self.assertTrue(
            hand.split(";", 1)[1].strip().startswith("physically plausible"),
            "staging material suffix must be carried over",
        )

    def test_never_show_covers_card_rules_and_extras(self):
        never = {x.lower() for x in self.bible["never_show"]}
        for term in ("readable text", "logo", "watermark", "nudity", "plastic skin", "two women", "extra limbs"):
            self.assertIn(term, never)
        self.assertIn("kiss close-up", never)  # staging extra
        hand = {x.lower() for x in self.seg["prompt_bible"]["never_show"]}
        uncovered = never - hand
        # two known card-vs-seg wording gaps, reported as DIFFs by crosscheck:
        # scene rules phrased longer than the hand-written seg terms
        self.assertEqual(
            {"extra person enters the bedroom", "new objects introduced beyond the visual anchors"},
            uncovered,
            f"only the two documented wording gaps may be uncovered: {uncovered}",
        )

    def test_crosscheck_segA_no_errors(self):
        report = crosscheck_bible(self.seg, self.cards, CAST, SCENE, self.staging)
        self.assertEqual([], report["errors"], f"segA migration must have zero errors: {report['errors']}")
        # the known card-side gap (scene 'no new objects' rule has no never_show
        # counterpart in the hand-written segA) is reported as a diff, not an error
        self.assertTrue(any("new objects" in d for d in report["diffs"]), report["diffs"])

    def test_v2_props_and_multi_file_merge(self):
        cards = load_cards_files([CARDS, CARDS_V2_PROPS])
        self.assertEqual(len(cards), 6)
        staging = {"subject_suffix": "the woman half-sits in bed", "never_show_extra": ["phone screen UI"]}
        bible = synth_prompt_bible(
            cards, ["char_woman"], SCENE, staging,
            prop_ids=["prop_phone", "prop_coffee_cup", "prop_note"],
        )
        self.assertNotIn("exactly two people", bible["subject_lock"])
        for frag in ("matte glass phone body", "matte ceramic cup", "soft warm paper note"):
            self.assertIn(frag, bible["material_lock"])
        for never in ("readable screen content", "phone screen UI"):
            self.assertIn(never, bible["never_show"])
        self.assertEqual(bible["_synthesis"]["props"], ["prop_phone", "prop_coffee_cup", "prop_note"])

    def test_props_must_be_prop_type(self):
        cards = load_cards_files([CARDS, CARDS_V2_PROPS])
        with self.assertRaises(ValueError):
            synth_prompt_bible(cards, ["char_woman"], SCENE, {}, prop_ids=[SCENE])

    def test_duplicate_ids_across_files_rejected(self):
        with self.assertRaises(ValueError):
            load_cards_files([CARDS, CARDS])

    def test_unknown_card_id_rejected(self):
        with self.assertRaises(ValueError):
            synth_prompt_bible(self.cards, ["char_ghost"], SCENE, {})

    def test_scene_in_cast_rejected(self):
        with self.assertRaises(ValueError):
            synth_prompt_bible(self.cards, ["char_woman", "scene_bedroom"], SCENE, {})

    def test_empty_cast_rejected_without_override(self):
        with self.assertRaises(ValueError):
            synth_prompt_bible(self.cards, [], SCENE, {})


class RuleMappingTest(unittest.TestCase):
    def test_negative_prefixes(self):
        self.assertEqual(rule_to_never("no nudity"), "nudity")
        self.assertEqual(rule_to_never("no extra limbs"), "extra limbs")

    def test_parenthetical_hard_fail_maps_to_term(self):
        self.assertEqual(rule_to_never("never a second woman in frame (two women = hard fail)"), "two women")

    def test_positive_rules_return_none(self):
        self.assertIsNone(rule_to_never("curtain openness and duvet rumple level stay consistent within a segment"))


class RefsManifestTest(unittest.TestCase):
    def test_manifest_hashes_reference_chain(self):
        manifest = build_refs_manifest(CARDS, IDENTITY)
        entry = manifest["cards"]["char_woman"]
        self.assertEqual("canonical_v6", entry["canonical_chain_version"])
        self.assertTrue(entry["files"], "canonical_v6 image files must be hashed")
        self.assertIn("front.png", entry["files"])
        self.assertTrue(all(len(h) == 64 for h in entry["files"].values()))


if __name__ == "__main__":
    unittest.main()
