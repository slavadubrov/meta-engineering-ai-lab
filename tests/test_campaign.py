"""Exercise the outer loop with scripted transport; never call a provider in tests."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from pydantic import ValidationError

from lab.__main__ import export_site
from lab.agent import Proposal, request_for, usage_cost, validate_proposal
from lab.campaign import context_for, run_campaigns
from lab.runner import ROOT, build_bundle, read_json, sha256


def decision(patch=None, action="propose"):
    return {
        "observations": [
            {
                "scenario_id": "future-move",
                "step": 3,
                "observation": "The returned city is not yet effective.",
            }
        ],
        "hypothesis": "Filtering the query may repair the observed answer.",
        "predicted_effect": "Test whether the complete-scenario score improves.",
        "action": action,
        "patch": {
            **dict.fromkeys(
                ("min_confidence", "filter_entity", "time_aware", "deduplicate", "top_k")
            ),
            **(patch or {}),
        },
    }


class ScriptedClient:
    def __init__(self, values):
        self.values = iter(values)
        self.requests = []
        self.responses = self

    def create(self, **request):
        self.requests.append(request)
        value = next(self.values)
        if isinstance(value, Exception):
            raise value
        response = {
            "id": "scripted-test",
            "model": "scripted-test",
            "status": "completed",
            "usage": {"input_tokens": 100, "output_tokens": 50},
            "output": [
                {"type": "message", "content": [{"type": "output_text", "text": json.dumps(value)}]}
            ],
        }
        return SimpleNamespace(model_dump=lambda **_: response)


class CampaignTests(unittest.TestCase):
    def test_feedback_changes_next_parent_and_rejected_candidate_does_not(self):
        client = ScriptedClient(
            [
                decision({"filter_entity": True, "time_aware": True}),
                # Cite supplied duplicate evidence after the first proposal repairs future-move.
                {
                    **decision({"min_confidence": 0.2}),
                    "observations": [
                        {
                            "scenario_id": "duplicate-confirmation",
                            "step": 1,
                            "observation": "Repeated writes remain.",
                        }
                    ],
                },
                {
                    **decision({"deduplicate": True}),
                    "observations": [
                        {
                            "scenario_id": "duplicate-confirmation",
                            "step": 1,
                            "observation": "Repeated writes remain.",
                        }
                    ],
                },
            ]
        )
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "campaign"
            result = run_campaigns(root, 1, 3, client=client)
            self.assertEqual(result["campaigns"][0]["scenario_executions"], 80)
            rows = result["campaigns"][0]["iterations"]
            self.assertEqual([r["status"] for r in rows], ["evaluated"] * 3)
            self.assertEqual([r["selected_for_next_iteration"] for r in rows], [True, False, True])
            self.assertEqual([r["parent_id"] for r in rows], ["baseline", "agent-01", "agent-01"])
            context = json.loads(client.requests[2]["input"])
            self.assertFalse(context["previous_iterations"][1]["selected"])
            self.assertEqual(len(json.loads(client.requests[0]["input"])["tested"]), 1)
            self.assertEqual(result["campaigns"][0]["selected"]["metrics"]["task_success"], 0.95)
            export_site(root / "campaign-01/baseline", Path(d) / "site", root)
            self.assertTrue((Path(d) / "site/memory.html").is_file())
            self.assertIn("./artifacts/campaign/", (Path(d) / "site/index.html").read_text())
            manifest = read_json(root / "manifest.json")
            self.assertTrue(all(sha256(root / f["path"]) == f["sha256"] for f in manifest["files"]))

    def test_budget_and_errors_are_recorded_without_silent_retries(self):
        with tempfile.TemporaryDirectory() as d:
            client = ScriptedClient([RuntimeError("never serialize a secret")])
            result = run_campaigns(Path(d) / "failed", 1, 3, client=client)
            self.assertEqual(len(client.requests), 1)
            self.assertEqual(result["campaigns"][0]["status"], "provider_error")
            self.assertGreater(result["charged_or_reserved_usd"], 0)
            self.assertNotIn("never serialize", json.dumps(result))
            empty = ScriptedClient([])
            result = run_campaigns(Path(d) / "budget", 1, 3, 0.000001, client=empty)
            self.assertEqual(empty.requests, [])
            self.assertEqual(result["campaigns"][0]["status"], "budget_exhausted")

    def test_cost_includes_cache_write_surcharge_and_unknown_is_not_zero(self):
        self.assertAlmostEqual(
            usage_cost(
                {
                    "input_tokens": 1000,
                    "output_tokens": 100,
                    "input_tokens_details": {"cache_write_tokens": 1000},
                }
            ),
            0.00037,
        )
        self.assertIsNone(usage_cost(None))

    def test_schema_permissions_evidence_and_stop(self):
        bundle, _ = build_bundle(lineage=[read_json(ROOT / "experiments/candidates.json")[0]])
        context = context_for(bundle, "baseline", [])
        valid = decision({"time_aware": True})
        self.assertEqual(validate_proposal(valid, context)[1], {"time_aware": True})
        for value in [
            {**valid, "patch": {**valid["patch"], "tenant_isolation": False}},
            decision({"time_aware": "true"}),
            decision({"top_k": 999}),
            decision({"filter_entity": True, "time_aware": True, "deduplicate": True}),
            {
                **valid,
                "observations": [{"scenario_id": "fabricated", "step": 1, "observation": "x"}],
            },
            decision({"time_aware": True}, "stop"),
        ]:
            with self.subTest(value=value), self.assertRaises((ValueError, ValidationError)):
                validate_proposal(value, context)
        self.assertEqual(validate_proposal(decision(action="stop"), context)[0].action, "stop")
        request = request_for(context)
        self.assertTrue(request["text"]["format"]["strict"])
        self.assertNotIn("tools", request)
        self.assertFalse(request["store"])

        def check(schema):
            if isinstance(schema, dict):
                if schema.get("type") == "object":
                    self.assertFalse(schema["additionalProperties"])
                    self.assertEqual(set(schema["properties"]), set(schema["required"]))
                for child in schema.values():
                    check(child)
            elif isinstance(schema, list):
                for child in schema:
                    check(child)

        check(Proposal.model_json_schema())
