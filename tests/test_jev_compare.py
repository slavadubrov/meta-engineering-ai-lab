"""Offline integration check: evidence, strict decisions, constraints, failure retention."""

import json
import tempfile
import unittest
from pathlib import Path

from lab.jev_compare import MODEL, NoRedirect, labels, run
from lab.runner import ROOT, read_json, verify


class JevComparisonTest(unittest.TestCase):
    def test_comparison_and_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            offline = run(root / "offline")
            self.assertEqual(offline["status"], "not_run")
            self.assertEqual(offline["arms"]["exact"]["score"]["agreement"], 8)
            self.assertEqual(offline["arms"]["exact_with_constraints"]["score"]["agreement"], 8)
            self.assertIsNone(offline["cost_usd"])
            verify(root / "offline")
            requests = []

            def send(request):
                requests.append(request)
                for case in request["state"]:
                    self.assertFalse(
                        {"semantic_accept", "reference_accept", "human_accept", "hard_failures"}
                        & case.keys()
                    )
                    self.assertFalse({"category"} & case.keys())
                return {
                    "model": MODEL + "-20260917",
                    "id": "synthetic-provider-id-not-for-export",
                    "usage": {"cost": 0.001, "input_tokens": 100, "output_tokens": 0},
                    "answers": {
                        cid: {"type": "choice", "choice": "accept", "confidence": 1}
                        for cid in request["questions"]
                    },
                }

            live = run(root / "stub", live=True, send=send)
            self.assertEqual(len(requests), 2)
            # Case IDs carry no label: the judge cannot read the answer category from them.
            self.assertTrue(all(key[0] == "c" for key in requests[0]["questions"]))
            self.assertNotIn("state_evidence", requests[0]["state"][0])
            self.assertIn("state_evidence", requests[1]["state"][0])
            self.assertEqual(live["status"], "completed")
            self.assertEqual(live["cost_usd"], 0.002)
            self.assertIn("confidence", live["calls"][0]["response"]["answers"]["c01"])
            restricted = [c["id"] for c in live["cases"] if c["hard_failures"]]
            self.assertEqual(len(restricted), 3)
            for cid in restricted:
                self.assertTrue(live["arms"]["jev_answer_only"]["predictions"][cid])
                self.assertFalse(live["arms"]["jev_with_constraints"]["predictions"][cid])
            self.assertNotIn("synthetic-provider-id", json.dumps(live))
            verify(root / "stub")
            with self.assertRaisesRegex(ValueError, "new output directory"):
                run(root / "stub")

            def fail(_):
                raise TimeoutError("Synthetic private provider detail must not be exported")

            with self.assertRaisesRegex(RuntimeError, "incomplete"):
                run(root / "failure", live=True, send=fail)
            failure = read_json(root / "failure/study.json")
            self.assertEqual(failure["status"], "incomplete")
            self.assertIsNone(failure["cost_usd"])
            self.assertEqual(failure["calls"][1]["status"], "not_run")
            self.assertNotIn("private provider detail", json.dumps(failure))
            verify(root / "failure")
            for name, response in (
                ("missing", {"model": MODEL, "answers": {}, "usage": {"cost": 0.001}}),
                ("nonfinite", {"model": MODEL, "usage": {"cost": float("nan")}}),
                ("other-model", {"model": "typesafe/jev-2", "answers": {}}),
            ):
                with self.assertRaises(RuntimeError):
                    run(root / name, live=True, send=lambda _, r=response: r)
                retained = read_json(root / name / "study.json")
                self.assertEqual(retained["status"], "incomplete")
                self.assertEqual(retained["calls"][1]["status"], "not_run")
                verify(root / name)
            for response in (
                {"answers": {}},
                {"answers": {"x": {"type": "choice", "choice": "maybe"}}},
            ):
                with self.assertRaises(ValueError):
                    labels(response, {"x"})
            with self.assertRaises(ValueError):
                NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.com")

    def test_frozen_live_study(self):
        frozen = ROOT / "reports/article-02/jev"
        verify(frozen)
        study = read_json(frozen / "study.json")
        self.assertEqual(study["status"], "completed")
        self.assertEqual(
            study["cases"], read_json(ROOT / "experiments/evaluator-exploits/judge-cases.json")
        )


if __name__ == "__main__":
    unittest.main()
