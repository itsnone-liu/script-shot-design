"""Preview timing checks only; no media generation and no approval changes."""
import unittest
from pathlib import Path
from unittest.mock import patch
from experiments import preview_coffee30_v2_unsent as preview


class PreviewTimingTest(unittest.TestCase):
    def test_hold_is_inside_contract_duration(self):
        docs = {name: preview.load_json(path) for name, path in preview.SEGMENTS.items()}
        fake = {f"KF_V2_N{i}": Path(f"N{i}.png") for i in range(1, 11)}
        fake["KF_V2_C_LAST"] = Path("last.png")
        with patch.object(preview, "registry_files", return_value=fake), patch.object(Path, "is_file", return_value=True):
            plan = preview.build_plan()
        self.assertAlmostEqual(sum(x["seconds"] for x in plan), sum(x["duration"] for x in docs.values()))
        self.assertTrue(all(x["seconds"] > 0 for x in plan))
        self.assertEqual(plan[-1]["shot_id"], "N10_hold")
        self.assertEqual(plan[-1]["seconds"], docs["C"]["final_hold_seconds"])


if __name__ == "__main__":
    unittest.main()
