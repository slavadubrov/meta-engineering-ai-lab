"""Regression checks for state isolation, bounded proposals, evidence and deterministic replay."""

import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from lab.memory import Config, Memory, MemoryRecord, validate_scenarios
from lab.runner import (
    ROOT,
    build_bundle,
    export,
    load_candidates,
    read_bundle,
    read_json,
    run_scenario,
    verify,
    verify_source,
)

# A person-supplied candidate: the same filters the Part 1 agent chose first.
DIAGNOSED = {
    "id": "diagnosed-history",
    "label": "Trace-diagnosed history",
    "parent_id": "baseline",
    "hypothesis": "Wrong-entity and out-of-date records answered queries.",
    "predicted_effect": "Repair the entity and temporal failures.",
    "patch": {"filter_entity": True, "time_aware": True},
    "proposer": {"type": "human", "name": "test", "model": "none", "prompt_version": "none"},
}


class ExperimentContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle, cls.runs = build_bundle()
        cls.candidates = {c["id"]: c for c in cls.bundle["candidates"]}
        cls.scenarios = read_json(ROOT / "data/scenarios.json")

    def test_default_is_one_run_per_scenario(self):
        bundle, runs = self.bundle, self.runs
        self.assertEqual(len(runs), 80)
        self.assertTrue(all(c["summary"]["repeat_count"] == 1 for c in bundle["candidates"]))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = root / "parent"
            export(parent, bundle, runs)
            proposal = root / "candidate.json"
            proposal.write_text(json.dumps(DIAGNOSED))
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

    def test_memory_schema_and_conflicts_cannot_corrupt_history(self):
        scenario = next(s for s in self.scenarios if s["id"] == "future-move")
        first, update = deepcopy(scenario["events"][:2])
        first["source_event_id"], update["source_event_id"] = "event-1", "event-2"
        memory = Memory(Config())
        self.assertEqual(memory.write(first)["status"], "stored")
        before = memory.snapshot()
        malformed = [
            {**update, "source_event_id": ""},
            {**update, "at": "20260103"},
            {**update, "fact": {**update["fact"], "confidence": float("nan")}},
            {**update, "fact": {**update["fact"], "confidence": True}},
            {**update, "fact": {**update["fact"], "extra": "ignored?"}},
        ]
        missing_source = deepcopy(update)
        del missing_source["source_event_id"]
        malformed.append(missing_source)
        for event in malformed:
            with self.subTest(event=event):
                self.assertEqual(memory.write(event)["reason"], "invalid_schema")
                self.assertEqual(memory.snapshot(), before)
                self.assertEqual(memory.next_id, 2)
        conflict = deepcopy(update)
        conflict["fact"]["valid_from"] = first["fact"]["valid_from"]
        self.assertEqual(memory.write(conflict)["reason"], "same_date_conflict")
        self.assertEqual(memory.snapshot(), before)
        self.assertEqual(memory.write(first)["reason"], "same_effective_fact")
        self.assertEqual(memory.snapshot(), before)
        late = deepcopy(update)
        late["fact"]["valid_from"] = "2025-12-31"
        self.assertEqual(memory.write(late)["reason"], "out_of_order_update")
        self.assertEqual(memory.snapshot(), before)
        self.assertEqual(memory.write(update)["status"], "stored")
        records = memory.snapshot()
        self.assertEqual(records[1]["supersedes_memory_id"], records[0]["id"])
        for record in records:
            self.assertEqual(MemoryRecord.model_validate(record).schema_version, 1)
        self.assertEqual(records[0]["valid_to"], records[1]["valid_from"])
        self.assertEqual(before[0]["valid_to"], None)
        for patch in (
            {"valid_to": records[0]["valid_from"]},
            {"valid_to": "2025-01-01"},
            {"schema_version": 2},
            {"schema_version": True},
            {"source_event_id": None},
        ):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                MemoryRecord.model_validate({**records[0], **patch})

    def test_delete_removes_history_and_allows_fresh_explicit_consent(self):
        scenario = next(s for s in self.scenarios if s["id"] == "delete-then-new-consent")
        run = run_scenario(scenario, Config(), 0)
        self.assertEqual(run["actual"], [None, "Paris"])
        self.assertEqual(run["after"][0]["id"], "m002")
        self.assertEqual(run["trace"][1]["after"], [])

    def test_repeated_runs_have_identical_state_and_answers(self):
        scenario = next(s for s in self.scenarios if s["id"] == "future-move")
        first, second = (run_scenario(scenario, Config(), repeat) for repeat in (0, 1))
        for field in ("trace", "actual", "after", "counts"):
            self.assertEqual(first[field], second[field])

    def test_frozen_release_hashes_and_person_supplied_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "release"
            export(path, self.bundle, self.runs)
            self.assertGreater(verify(path), 100)
            self.assertEqual(verify_source(path)["release_id"], self.bundle["release_id"])
            with self.assertRaises(FileExistsError):
                export(path, self.bundle, self.runs)
            bundle, _ = build_bundle(extra=DIAGNOSED)
            self.assertEqual(
                bundle["candidates"][-1]["summary"]["metrics"]["task_success"],
                self.candidates["scoped-history"]["summary"]["metrics"]["task_success"],
            )
            (path / "metrics.json").write_text(json.dumps({"tampered": True}))
            with self.assertRaises(ValueError):
                verify(path)

    def test_source_check_compares_only_recorded_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "release"
            export(path, self.bundle, self.runs)
            manifest = read_json(path / "manifest.json")
            # A file added after the release does not count as a change.
            manifest["provenance"]["source_files"].pop("lab/jev_compare.py")
            (path / "manifest.json").write_text(json.dumps(manifest))
            verify_source(path)
            manifest["provenance"]["source_files"]["lab/memory.py"] = "0" * 64
            (path / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "lab/memory.py"):
                verify_source(path)

    def test_part1_article_numbers_still_reproduce(self):
        """The current code gives the scores recorded for article 1 (quality only, not timing)."""
        recorded = ROOT / "artifacts/article-01.6/bundle.json"
        if not recorded.exists():
            self.skipTest("Run scripts/fetch_evidence.py to download the Part 1 evidence")
        frozen = read_json(recorded, max_bytes=64_000_000)
        timing = {"latency_p50_ms", "latency_p95_ms"}
        for current, old in zip(self.bundle["candidates"], frozen["candidates"], strict=True):
            self.assertEqual(current["id"], old["id"])
            for key, value in old["summary"]["metrics"].items():
                if key not in timing and key in current["summary"]["metrics"]:
                    self.assertEqual(current["summary"]["metrics"][key], value, (old["id"], key))
            self.assertEqual(
                current["summary"]["hard_constraints"], old["summary"]["hard_constraints"]
            )
        campaigns = read_json(ROOT / "artifacts/agent-study-03/campaigns.json")
        for campaign in campaigns["campaigns"]:
            config = Config(**campaign["selected"]["config"])
            runs = [run_scenario(s, config, 0) for s in self.scenarios]
            self.assertEqual(
                sum(r["success"] for r in runs) / len(runs),
                campaign["selected"]["metrics"]["task_success"],
            )

    def test_two_generation_cli_and_eight_candidate_feedback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = root / "generation-0"
            export(parent, self.bundle, self.runs)
            proposal = DIAGNOSED
            child, runs = build_bundle(extra=proposal, parent_release=parent)
            first = root / "generation-1"
            export(first, child, runs)
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
                bundle, runs = build_bundle(extra=candidate, parent_release=parent)
                parent = root / next_id
                export(parent, bundle, runs)
                parent_id = next_id
            self.assertEqual(len(bundle["candidates"]), 8)
            self.assertGreater((parent / "bundle.json").stat().st_size, 2_000_000)
            with self.assertRaises(ValueError):
                build_bundle(extra={**proposal, "id": "ninth"}, parent_release=parent)
            manifest = read_json(parent / "manifest.json")
            manifest["provenance"]["source_files"]["lab/runner.py"] = "0" * 64
            (parent / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "Current source differs"):
                build_bundle(extra=proposal, parent_release=parent)

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
                    "--release",
                    str(root),
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
