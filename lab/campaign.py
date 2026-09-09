"""Run independent LLM improvement campaigns over the existing deterministic evaluator."""

import json
import math
import time
from datetime import UTC, datetime
from pathlib import Path

from .agent import (
    MODEL,
    PRICING_SOURCE,
    PROMPT_VERSION,
    live_client,
    request_for,
    reserve_usd,
    usage_cost,
    validate_proposal,
)
from .runner import ROOT, build_bundle, dump, export, provenance, read_json, sha256, verify


def feedback(candidate: dict) -> dict:
    return {
        "id": candidate["id"],
        "config": candidate["config"],
        "metrics": candidate["summary"]["metrics"],
        "hard_constraints": candidate["summary"]["hard_constraints"],
        "recommendation": candidate["recommendation"],
    }


def context_for(bundle: dict, parent_id: str, history: list[dict]) -> dict:
    parent = next(c for c in bundle["candidates"] if c["id"] == parent_id)
    return {
        "parent_id": parent_id,
        "parent_config": parent["config"],
        "permissions": {
            k: v
            for k, v in read_json(ROOT / "experiments/contract.json").items()
            if k in {"mutable_surface", "immutable"}
        },
        "exposure": "All 20 scenarios are public development cases. No held-out claim.",
        "tested": [feedback(c) for c in bundle["candidates"]],
        "previous_iterations": history,
        # All failed stories plus write rejections and duplicate confirmations make
        # the quality/storage tradeoff inspectable without handing over ready-made fixes.
        "evidence": [
            {
                "scenario_id": r["scenario_id"],
                "actual": r["actual"],
                "expected": r["expected"],
                "trace": [
                    {k: e[k] for k in ("step", "action", "detail", "result", "after")}
                    for e in r["trace"]
                ],
            }
            for r in parent["runs"]
            if not r["success"]
            or any(
                e["action"] == "write" and e["result"]["status"] in {"abstained", "deduplicated"}
                for e in r["trace"]
            )
            or r["scenario_id"] == "duplicate-confirmation"
        ],
    }


def response_text(response: dict) -> str:
    if response.get("status") != "completed":
        raise ValueError("Provider response did not complete")
    contents = [
        c
        for item in response.get("output", [])
        if item.get("type") == "message"
        for c in item.get("content", [])
    ]
    if any(c.get("type") == "refusal" for c in contents):
        raise ValueError("Provider refused the proposal")
    texts = [c["text"] for c in contents if c.get("type") == "output_text"]
    if len(texts) != 1:
        raise ValueError("Expected one structured proposal")
    return texts[0]


def run_campaigns(
    output: Path, campaigns: int = 3, iterations: int = 4, budget_usd: float = 0.5, *, client=None
) -> dict:
    if type(campaigns) is not int or not 1 <= campaigns <= 5:
        raise ValueError("Campaign count must be between 1 and 5")
    if type(iterations) is not int or not 1 <= iterations <= 4:
        raise ValueError("Iteration count must be between 1 and 4")
    if not math.isfinite(budget_usd) or not 0 < budget_usd <= 2:
        raise ValueError("Budget must be above zero and at most USD 2")
    client = client if client is not None else live_client()
    output.mkdir(parents=True, exist_ok=False)
    identity = provenance()
    experiment = {
        "schema_version": "agent-campaign-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "model": MODEL,
        "prompt_version": PROMPT_VERSION,
        "source": identity,
        "planned_campaigns": campaigns,
        "max_iterations": iterations,
        "budget_usd": budget_usd,
        "estimated_cost_usd": 0.0,
        "charged_or_reserved_usd": 0.0,
        "pricing_source": PRICING_SOURCE,
        "pricing_checked": "2026-09-09",
        "status": "running",
        "campaigns": [],
        "exposure": "Public development stories; no hidden evaluation set.",
        "review": "Experiment selection only; every deployment decision remains pending human review.",
    }
    dump(output / "campaigns.json", experiment)
    try:
        for number in range(1, campaigns + 1):
            path = output / f"campaign-{number:02d}"
            path.mkdir()
            bundle, runs = build_bundle(
                lineage=[read_json(ROOT / "experiments/candidates.json")[0]]
            )
            release = path / "baseline"
            bundle["release_id"] = release.name
            export(release, bundle, runs)
            current = "baseline"
            campaign = {
                "id": path.name,
                "status": "running",
                "iterations": [],
                "baseline": feedback(bundle["candidates"][0]),
                "scenario_executions": len(runs),
            }
            experiment["campaigns"].append(campaign)
            history = []
            for iteration in range(1, iterations + 1):
                step = path / f"iteration-{iteration:02d}"
                step.mkdir()
                context = context_for(bundle, current, history)
                request = request_for(context)
                reservation = reserve_usd(request)
                if experiment["charged_or_reserved_usd"] + reservation > budget_usd:
                    campaign["status"] = "budget_exhausted"
                    break
                if provenance()["source_files"] != identity["source_files"]:
                    raise ValueError("Source changed during the campaign")
                dump(step / "request.json", request)
                record = {
                    "iteration": iteration,
                    "parent_id": current,
                    "status": "calling",
                    "path": str(step.relative_to(output)),
                    "reserved_usd": reservation,
                }
                campaign["iterations"].append(record)
                experiment["charged_or_reserved_usd"] += reservation
                dump(output / "campaigns.json", experiment)
                started = time.monotonic()
                try:
                    response = client.responses.create(**request).model_dump(mode="json")
                except Exception as error:
                    # Do not serialize provider exception text: it may include request secrets.
                    record.update(
                        status="provider_error",
                        error_type=type(error).__name__,
                        latency_seconds=time.monotonic() - started,
                        cost_status="unknown; full reservation retained",
                    )
                    campaign["status"] = "provider_error"
                    dump(step / "result.json", record)
                    break
                record["latency_seconds"] = time.monotonic() - started
                dump(step / "response.json", response)
                cost = usage_cost(response.get("usage"))
                record.update(
                    usage=response.get("usage"),
                    estimated_cost_usd=cost,
                    response_model=response.get("model"),
                )
                if cost is not None:
                    experiment["estimated_cost_usd"] += cost
                    experiment["charged_or_reserved_usd"] += cost - reservation
                phase = "proposal"
                returned_text = ""
                try:
                    returned_text = response_text(response)
                    proposal, patch = validate_proposal(json.loads(returned_text), context)
                    dump(step / "proposal.json", proposal.model_dump())
                    if proposal.action == "stop":
                        record.update(status="agent_stopped", reason=proposal.hypothesis)
                        campaign["status"] = "agent_stopped"
                        dump(step / "result.json", record)
                        break
                    candidate = dict(
                        id=f"agent-{iteration:02d}",
                        label=f"Agent proposal {iteration}",
                        parent_id=current,
                        hypothesis=proposal.hypothesis,
                        predicted_effect=proposal.predicted_effect,
                        patch=patch,
                        proposer=dict(
                            type="llm",
                            name="OpenAI",
                            model=response.get("model", MODEL),
                            prompt_version=PROMPT_VERSION,
                            response_id=response.get("id", "unknown"),
                        ),
                    )
                    dump(step / "candidate.json", candidate)
                    phase = "evaluation"
                    next_bundle, next_runs = build_bundle(extra=candidate, parent_release=release)
                    campaign["scenario_executions"] += len(next_bundle["scenarios"])
                    evaluated = next_bundle["candidates"][-1]
                    release = step / "evaluation"
                    next_bundle["release_id"] = release.name
                    export(release, next_bundle, next_runs)
                    verify(release)
                    bundle = next_bundle
                    selected = evaluated["recommendation"]["status"] == "recommend_accept"
                    record.update(
                        status="evaluated",
                        patch=patch,
                        feedback=feedback(evaluated),
                        selected_for_next_iteration=selected,
                    )
                    if selected:
                        current = candidate["id"]
                    history.append(
                        {
                            "iteration": iteration,
                            "proposal": proposal.model_dump(),
                            "feedback": record["feedback"],
                            "selected": selected,
                        }
                    )
                except (ValueError, TypeError, KeyError) as error:
                    if phase == "evaluation":
                        record.update(status="evaluation_error", reason=str(error)[:1500])
                        campaign["status"] = "evaluation_error"
                        dump(step / "result.json", record)
                        break
                    record.update(status="invalid_proposal", reason=str(error)[:1500])
                    history.append(
                        {
                            "iteration": iteration,
                            "rejected_output": returned_text,
                            "rejection": record["reason"],
                        }
                    )
                dump(step / "result.json", record)
                dump(output / "campaigns.json", experiment)
                if cost is None:
                    campaign["status"] = "usage_unavailable"
                    break
            else:
                campaign["status"] = "iteration_limit"
            final = next(c for c in bundle["candidates"] if c["id"] == current)
            campaign["selected"] = feedback(final)
            campaign["final_release"] = str(release.relative_to(output))
            dump(output / "campaigns.json", experiment)
        experiment["status"] = (
            "completed_with_errors"
            if any(
                c["status"] in {"provider_error", "usage_unavailable", "evaluation_error"}
                for c in experiment["campaigns"]
            )
            else "completed"
        )
    except BaseException:
        experiment["status"] = "interrupted"
        raise
    finally:
        dump(output / "campaigns.json", experiment)
        write_campaign_report(output, experiment)
        dump(
            output / "manifest.json",
            {
                "provenance": identity,
                "files": [
                    {"path": str(p.relative_to(output)), "sha256": sha256(p)}
                    for p in sorted(output.rglob("*"))
                    if p.is_file() and p != output / "manifest.json"
                ],
            },
        )
    return experiment


def write_campaign_report(output: Path, experiment: dict) -> None:
    lines = [
        "# LLM memory improvement campaigns",
        "",
        "The outer agent proposes changes; deterministic Python measures them. "
        "Every campaign starts from the same baseline with fresh history.",
        "",
        f"Model: `{experiment['model']}`. Prompt: `{experiment['prompt_version']}`.",
        "",
        "| Campaign | Outcome | Selected success | Model calls |",
        "| --- | --- | ---: | ---: |",
    ]
    for c in experiment["campaigns"]:
        score = c.get("selected", c["baseline"])["metrics"]["task_success"]
        lines.append(f"| {c['id']} | {c['status']} | {score:.0%} | {len(c['iterations'])} |")
    for c in experiment["campaigns"]:
        for r in c["iterations"]:
            lines.extend(
                [
                    "",
                    f"## {c['id']} / iteration {r['iteration']}",
                    "",
                    f"Status: **{r['status']}**. Parent: `{r['parent_id']}`.",
                    "",
                    f"[Exact request]({r['path']}/request.json) · "
                    f"[Recorded outcome]({r['path']}/result.json)",
                ]
            )
            if "patch" in r:
                lines.extend(
                    [
                        "",
                        f"Patch: `{json.dumps(r['patch'])}`.",
                        "",
                        f"Success: {r['feedback']['metrics']['task_success']:.0%}. "
                        f"Selected for next iteration: {r['selected_for_next_iteration']}.",
                        "",
                        f"[Proposal]({r['path']}/proposal.json) · "
                        f"[Evaluation]({r['path']}/evaluation/report.html)",
                    ]
                )
    lines.extend(
        [
            "",
            "## Limits and cost",
            "",
            "All 20 stories are public development inputs. These campaigns do not "
            "establish held-out generalization or an advantage over manual tuning.",
            "",
            f"Estimated model cost (cache-write surcharge included; read discounts ignored): ${experiment['estimated_cost_usd']:.6f}. "
            f"Cost plus unknown-call reservations: ${experiment['charged_or_reserved_usd']:.6f}. "
            "Provider failures remain in the record; unknown cost is not zero.",
            "",
            "Selection only changes the next experimental parent. Nothing is deployed; "
            "human release review is still required.",
            "",
        ]
    )
    (output / "report.md").write_text("\n".join(lines))
