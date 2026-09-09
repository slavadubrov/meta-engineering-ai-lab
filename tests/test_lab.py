"""Regression checks for state isolation, bounded proposals, evidence and deterministic replay."""

import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch as mock_patch

from lab.__main__ import export_site, proposal_context, propose
from lab.memory import Config, validate_scenarios
from lab.runner import (
    ROOT,
    build_bundle,
    export,
    load_candidates,
    read_bundle,
    read_json,
    run_scenario,
    verify,
)


class ExperimentContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle, cls.runs = build_bundle(repeats=2)
        cls.candidates = {c["id"]: c for c in cls.bundle["candidates"]}
        cls.scenarios = read_json(ROOT / "data/scenarios.json")

    def test_default_is_one_run_per_scenario(self):
        bundle, runs = build_bundle()
        self.assertEqual(len(runs), 80)
        self.assertTrue(all(c["summary"]["repeat_count"] == 1 for c in bundle["candidates"]))
        self.assertTrue(
            all(
                c["summary"]["metrics"]["success_repeat_stddev"] is None
                for c in bundle["candidates"]
            )
        )
        self.assertEqual(read_json(ROOT / "experiments/contract.json")["default_repeats"], 1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = root / "parent"
            export(parent, bundle, runs)
            proposal = root / "candidate.json"
            proposal.write_text(json.dumps(propose(proposal_context(parent, "baseline"))))
            for command, extra, expected in (
                ("run", [], 80),
                ("evaluate", ["--release", str(parent), "--candidate", str(proposal)], 100),
            ):
                output = root / command
                result = subprocess.run(
                    [sys.executable, "-m", "lab", command, "--output", str(output), *extra],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(len((output / "runs.jsonl").read_text().splitlines()), expected)

    def test_observed_quality_proxy_and_neutral_outcomes(self):
        base = self.candidates["baseline"]["summary"]["metrics"]
        scoped = self.candidates["scoped-history"]["summary"]["metrics"]
        neutral = self.candidates["deduplicated"]["summary"]["metrics"]
        broad = self.candidates["broad-writes"]["summary"]["metrics"]
        self.assertGreater(scoped["task_success"], base["task_success"])
        self.assertEqual(neutral["task_success"], scoped["task_success"])
        self.assertLess(neutral["storage_records"], scoped["storage_records"])
        self.assertGreater(broad["useful_write_recall"], scoped["useful_write_recall"])
        self.assertLess(broad["task_success"], scoped["task_success"])

    def test_isolation_deletion_and_prohibited_writes_are_nonnegotiable(self):
        for candidate in self.candidates.values():
            for constraint in candidate["summary"]["hard_constraints"].values():
                self.assertTrue(constraint["passed"])
                self.assertGreater(constraint["checks"], 0)
            self.assertEqual(candidate["decision"]["status"], "pending_human_review")
            self.assertIsNone(candidate["decision"]["actor"])
        for proposal in self.bundle["blocked_proposals"]:
            with self.assertRaises(ValueError):
                Config().patch(proposal["patch"])

    def test_invalid_config_cannot_enter_candidate(self):
        for patch in (
            {"min_confidence": float("nan")},
            {"top_k": True},
            {"filter_entity": "false"},
            {"min_confidence": True},
            {"min_confidence": 1.1},
            {"time_aware": None},
            {"__class__": "Injected"},
        ):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                Config().patch(patch)
        extra = deepcopy(read_json(ROOT / "experiments/candidates.json")[1])
        extra["id"] = "new-candidate"
        extra["parent_id"] = "missing-parent"
        with self.assertRaises(ValueError):
            load_candidates(extra)
        with self.assertRaises(ValueError):
            build_bundle(repeats=6)

    def test_dates_are_canonical_before_lexical_comparison(self):
        scenarios = deepcopy(self.scenarios)
        scenarios[0]["events"][0]["at"] = "20260101"
        with self.assertRaises(ValueError):
            validate_scenarios(scenarios)
        scenarios[0]["events"][0]["at"] = "2026-02-30"
        with self.assertRaises(ValueError):
            validate_scenarios(scenarios)

    def test_history_uses_effective_date_and_preserves_write_provenance(self):
        scenario = next(s for s in self.scenarios if s["id"] == "future-move")
        baseline = run_scenario(scenario, Config(), 0)
        scoped = run_scenario(scenario, Config(filter_entity=True, time_aware=True), 0)
        self.assertEqual(baseline["actual"], ["Paris", "Paris"])
        self.assertEqual(scoped["actual"], ["Berlin", "Paris"])
        self.assertEqual(scoped["after"][0]["valid_to"], "2026-01-10")
        self.assertEqual(scoped["after"][0]["source_event_id"], "future-move:event-1")
        boundary = next(s for s in self.scenarios if s["id"] == "history-boundary")
        self.assertTrue(run_scenario(boundary, Config(time_aware=True), 0)["success"])

    def test_delete_removes_history_and_allows_fresh_explicit_consent(self):
        scenario = next(s for s in self.scenarios if s["id"] == "delete-then-new-consent")
        run = run_scenario(scenario, Config(), 0)
        self.assertEqual(run["actual"], [None, "Paris"])
        self.assertEqual(run["after"][0]["id"], "m002")
        self.assertEqual(run["trace"][1]["after"], [])

    def test_repeats_have_identical_state_and_answers(self):
        first = {(r["candidate_id"], r["scenario_id"]): r for r in self.runs if r["repeat"] == 0}
        for run in (r for r in self.runs if r["repeat"] == 1):
            parent = first[run["candidate_id"], run["scenario_id"]]
            for field in ("trace", "actual", "after", "counts"):
                self.assertEqual(run[field], parent[field])
        self.assertTrue(
            all(
                c["summary"]["metrics"]["success_repeat_stddev"] == 0
                for c in self.candidates.values()
            )
        )

    def test_frozen_release_hashes_and_trace_driven_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "release"
            export(path, self.bundle, self.runs)
            self.assertGreater(verify(path), 100)
            site = Path(directory) / "site"
            export_site(path, site)
            self.assertIn("./artifacts/release/", (site / "index.html").read_text())
            self.assertNotIn("../artifacts/article-01.5/", (site / "index.html").read_text())
            self.assertEqual(verify(site / "artifacts/release"), verify(path))
            with self.assertRaises(FileExistsError):
                export(path, self.bundle, self.runs)
            context = proposal_context(path, "baseline")
            self.assertTrue(all(r["role"] == "search" for r in context["failures"]))
            candidate = propose(context)
            self.assertEqual(candidate["patch"], {"filter_entity": True, "time_aware": True})
            self.assertEqual(candidate["proposer"]["type"], "rule_based")
            bundle, _ = build_bundle(repeats=1, extra=candidate)
            self.assertEqual(
                bundle["candidates"][-1]["summary"]["metrics"]["task_success"],
                self.candidates["scoped-history"]["summary"]["metrics"]["task_success"],
            )
            (path / "metrics.json").write_text(json.dumps({"tampered": True}))
            with self.assertRaises(ValueError):
                verify(path)

    def test_two_generation_cli_and_eight_candidate_feedback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = root / "generation-0"
            export(parent, self.bundle, self.runs)
            proposal = propose(proposal_context(parent, "baseline"))
            child, runs = build_bundle(repeats=1, extra=proposal, parent_release=parent)
            first = root / "generation-1"
            export(first, child, runs)
            context = proposal_context(first, "diagnosed-history")
            self.assertEqual(context["parent_config"]["filter_entity"], True)
            second_proposal = {
                **proposal,
                "id": "second-generation",
                "parent_id": "diagnosed-history",
                "patch": {"deduplicate": True},
            }
            proposal_path = root / "candidate.json"
            proposal_path.write_text(json.dumps(second_proposal))
            second = root / "generation-2"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lab",
                    "evaluate",
                    "--release",
                    str(first),
                    "--candidate",
                    str(proposal_path),
                    "--output",
                    str(second),
                    "--repeats",
                    "1",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            bundle = read_bundle(second)
            self.assertEqual(len(bundle["candidates"]), 6)
            self.assertEqual(bundle["candidates"][4]["proposer"], proposal["proposer"])
            self.assertEqual(bundle["candidates"][-1]["parent_id"], "diagnosed-history")
            self.assertEqual(bundle["parent_release"]["release_id"], child["release_id"])
            parent = second
            parent_id = "second-generation"
            for number in (3, 4):
                next_id = f"generation-{number}"
                candidate = {
                    **proposal,
                    "id": next_id,
                    "parent_id": parent_id,
                    "patch": {"top_k": number},
                }
                bundle, runs = build_bundle(repeats=1, extra=candidate, parent_release=parent)
                parent = root / next_id
                export(parent, bundle, runs)
                parent_id = next_id
            self.assertEqual(len(bundle["candidates"]), 8)
            self.assertGreater((parent / "bundle.json").stat().st_size, 2_000_000)
            self.assertEqual(proposal_context(parent, parent_id)["parent_id"], parent_id)
            with self.assertRaises(ValueError):
                build_bundle(repeats=1, extra={**proposal, "id": "ninth"}, parent_release=parent)
            with mock_patch(
                "lab.runner.provenance", return_value={"source_files": {"changed": "hash"}}
            ):
                with self.assertRaisesRegex(ValueError, "Current source differs"):
                    build_bundle(repeats=1, extra=proposal, parent_release=parent)

    def test_cli_null_candidate_is_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "null.json"
            path.write_text("null")
            output = root / "must-not-exist"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lab",
                    "evaluate",
                    "--candidate",
                    str(path),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("must be a JSON object", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
