"""Tests for methods_promote (learning-loop write-back arm)."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shortfilm.cli import methods_promote  # noqa: E402

CARD = {
    "id": "method.test-card",
    "version": 0,
    "kind": "method",
    "lifecycle": "candidate",
    "title": "test",
    "problem": "p",
    "intended_effect": "e",
    "applicability": [],
    "exclusions": [],
    "procedure": [],
    "acceptance_tests": [],
    "failure_modes": [],
    "provenance": [],
    "evidence_refs": [],
    "consumers": [],
}


class MethodsPromoteTest(unittest.TestCase):
    def setUp(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        card = json.loads(json.dumps(CARD))
        (self.dir / "method.test-card.json").write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *argv: str) -> int:
        import contextlib, io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                code = methods_promote.main([*argv, "--dir", str(self.dir)])
            except SystemExit:
                code = 4
        return code

    def test_promote_candidate_to_testted(self):
        self.assertEqual(0, self._run("--id", "method.test-card", "--to", "tested", "--evidence", "piece A blind review"))
        card = json.loads((self.dir / "method.test-card.json").read_text(encoding="utf-8"))
        self.assertEqual(card["lifecycle"], "tested")
        self.assertEqual(card["version"], 1)
        self.assertEqual(card["evidence_refs"][0]["claim"], "piece A blind review")
        self.assertEqual(card["evidence_refs"][0]["from"], "candidate")

    def test_forward_only(self):
        self.assertEqual(0, self._run("--id", "method.test-card", "--to", "tested", "--evidence", "first"))
        self.assertEqual(2, self._run("--id", "method.test-card", "--to", "tested", "--evidence", "again"))
        card = json.loads((self.dir / "method.test-card.json").read_text(encoding="utf-8"))
        self.assertEqual(card["lifecycle"], "tested")
        self.assertEqual(len(card["evidence_refs"]), 1)

    def test_verified_climbs_from_tested(self):
        self.assertEqual(0, self._run("--id", "method.test-card", "--to", "tested", "--evidence", "A"))
        self.assertEqual(0, self._run("--id", "method.test-card", "--to", "verified", "--evidence", "B cross-piece"))
        card = json.loads((self.dir / "method.test-card.json").read_text(encoding="utf-8"))
        self.assertEqual(card["lifecycle"], "verified")
        self.assertEqual(card["version"], 2)

    def test_missing_card_refused(self):
        self.assertNotEqual(0, self._run("--id", "method.ghost", "--to", "tested", "--evidence", "x"))


if __name__ == "__main__":
    unittest.main()
