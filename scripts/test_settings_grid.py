"""Settings-grid checks kept outside the frozen evaluator's tests/*.py source inventory."""

import json
import unittest

from settings_grid import REPORT, SUMMARY, build, summary


class SettingsGridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build()

    def test_saved_reports_are_current(self):
        self.assertEqual(json.loads(REPORT.read_text()), self.report)
        self.assertEqual(SUMMARY.read_text(), summary(self.report))

    def test_grid_finds_the_agent_configuration(self):
        grid = self.report["grid"]
        self.assertEqual(grid["configurations"], 384)
        self.assertEqual(grid["passing_all"], 16)
        self.assertFalse(grid["top_k_changes_result"])
        self.assertTrue(grid["best_matches_agent_final"])
        self.assertEqual(grid["best_mean_storage_records"], 1.65)

    def test_single_settings_match_recorded_campaign_steps(self):
        passed = {row["label"]: row["passed"] for row in self.report["single_settings"]}
        self.assertEqual(passed["Baseline"], 13)
        self.assertEqual(passed["Both filters"], 19)
        self.assertEqual(passed["Agent's final configuration"], 20)


if __name__ == "__main__":
    unittest.main()
