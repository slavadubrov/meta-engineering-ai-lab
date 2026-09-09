"""Evaluate fixed scenarios, preserve evidence, and export an inspectable static release."""

import hashlib
import html
import json
import platform
import statistics
import subprocess
import sys
import time
from collections import Counter
from copy import deepcopy
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from .memory import ALLOWED_KEYS, Config, Memory, scope, valid_at, validate_scenarios

ROOT = Path(__file__).resolve().parents[1]
MAX_REPEATS = 5
MAX_CANDIDATES = 8
MAX_WALL_SECONDS = 30
MAX_ARTIFACT_JSON_BYTES = 64_000_000
METRICS = {
    "task_success": (
        "Downstream success",
        "fraction",
        "Scenarios with every answer correct and all implemented hard-constraint checks passing",
        "higher",
    ),
    "useful_write_precision": (
        "Useful-write precision",
        "fraction",
        "Useful retained proposals / all retained proposals",
        "higher",
    ),
    "useful_write_recall": (
        "Useful-write recall",
        "fraction",
        "Useful retained proposals / useful proposals",
        "higher",
    ),
    "unnecessary_write_rate": (
        "Unnecessary-write rate",
        "fraction",
        "Unnecessary retained / unnecessary proposals",
        "lower",
    ),
    "relevant_memory_recall": (
        "Relevant-memory recall",
        "fraction",
        "Answered-fact queries retrieving correct scoped, valid evidence / queries requiring a fact",
        "higher",
    ),
    "distracting_memory_rate": (
        "Distracting-memory rate",
        "fraction",
        "Retrieved records not matching the expected scoped and dated fact / retrieved records",
        "lower",
    ),
    "stale_fact_rate": (
        "Stale/future fact rate",
        "fraction",
        "Answers supported by a record invalid at the requested date / queries",
        "lower",
    ),
    "update_correctness": (
        "Update correctness",
        "fraction",
        "Correct answers in the update family / update queries",
        "higher",
    ),
    "context_words": (
        "Mean context words",
        "words",
        "Whitespace-delimited context words per query; not model tokens",
        "lower",
    ),
    "storage_records": (
        "Mean stored records",
        "records",
        "Final records per independent scenario",
        "lower",
    ),
    "storage_bytes": (
        "Mean stored bytes",
        "bytes",
        "UTF-8 compact JSON bytes in the final state per scenario",
        "lower",
    ),
    "latency_p50_ms": (
        "Local p50 latency",
        "ms",
        "Nearest-rank median of scenario execution, excluding export; no provider call",
        "lower",
    ),
    "latency_p95_ms": (
        "Local p95 latency",
        "ms",
        "Nearest-rank p95 of scenario execution, excluding export; noisy local timing",
        "lower",
    ),
    "provider_cost_usd": (
        "Provider expenditure",
        "USD",
        "Zero API calls; excludes hardware, energy and authoring effort",
        "lower",
    ),
    "model_tokens": (
        "Model tokens",
        "tokens",
        "Zero: normalized proposals and a deterministic consumer",
        "lower",
    ),
    "success_repeat_stddev": (
        "Repeat success stddev",
        "fraction",
        "Population standard deviation across repeated deterministic sweeps; not statistical generalization",
        "lower",
    ),
}
LIMITATIONS = [
    "All scenarios are original synthetic public fixtures visible during candidate authorship. Search/evaluation/adversarial roles are regression and validation organization, not blind held-out sets.",
    "This target starts from structured fact proposals. Confidence scores are hand-authored fixture values, not calibrated probabilities. It does not measure language extraction, model calibration, or a real assistant's reasoning.",
    "The frozen consumer returns the first packed fact with the requested key. Its failure modes are inspectable; they do not estimate a language model's behavior.",
    "Scoped history changes entity and temporal filtering together. Its gain is attributable to the tested bundle; this run does not estimate the isolated effect of each switch.",
    "Each scenario runs once by default. Repeating these deterministic rules adds no answer-quality evidence; variation across repeats is unavailable for a single run.",
    "Configuration validation limits what these manifests can change. This same-user process is not an operating-system sandbox against a malicious coding agent with filesystem access.",
    "The durable-key/source/kind gate rejects the supplied structured attacks. It is not a general prompt-injection defense or a detector for secrets hidden in allowed values.",
    "Latency is local execution of tiny in-memory scenarios. Context words are not model tokens. Zero provider expenditure excludes authoring, machine and electricity costs.",
    "Recommendations require human review. Running an experiment does not grant approval, change production, publish a repository, or deploy a service.",
]


def read_json(path: Path, max_bytes: int = 2_000_000):
    if path.stat().st_size > max_bytes:
        raise ValueError(f"JSON exceeds its {max_bytes:,}-byte input limit")
    return json.loads(path.read_text())


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state_diff(before: list[dict], after: list[dict]) -> dict:
    old, new = ({r["id"]: r for r in records} for records in (before, after))
    return {
        "added": [record for key, record in new.items() if key not in old],
        "removed": [record for key, record in old.items() if key not in new],
        "changed": [
            {"id": key, "before": old[key], "after": record}
            for key, record in new.items()
            if key in old and old[key] != record
        ],
    }


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def metrics(counts: Counter, latencies: list[float], repeat_scores: list[float]) -> dict:
    sorted_times = sorted(latencies)

    def percentile(p: float) -> float:
        import math

        return sorted_times[max(0, math.ceil(p * len(sorted_times)) - 1)]

    return {
        "task_success": ratio(counts["successes"], counts["tasks"]),
        "useful_write_precision": ratio(counts["useful_retained"], counts["retained"]),
        "useful_write_recall": ratio(counts["useful_retained"], counts["useful_proposals"]),
        "unnecessary_write_rate": ratio(
            counts["unnecessary_retained"], counts["unnecessary_proposals"]
        ),
        "relevant_memory_recall": ratio(counts["recalled"], counts["fact_queries"]),
        "distracting_memory_rate": ratio(counts["distractors"], counts["retrieved"]),
        "stale_fact_rate": ratio(counts["stale_answers"], counts["queries"]),
        "update_correctness": ratio(counts["correct_updates"], counts["update_queries"]),
        "context_words": ratio(counts["context_words"], counts["queries"]),
        "storage_records": ratio(counts["storage_records"], counts["tasks"]),
        "storage_bytes": ratio(counts["storage_bytes"], counts["tasks"]),
        "latency_p50_ms": percentile(0.5),
        "latency_p95_ms": percentile(0.95),
        "provider_cost_usd": 0,
        "model_tokens": 0,
        "success_repeat_stddev": statistics.pstdev(repeat_scores)
        if len(repeat_scores) > 1
        else None,
    }


def run_scenario(scenario: dict, config: Config, repeat: int) -> dict:
    target = Memory(config)
    trace, actual, expected = [], [], []
    counts = Counter(tasks=1)
    constraints = {
        name: {"passed": True, "violations": 0, "checks": 0}
        for name in ("owner_isolation", "deletion", "prohibited_writes")
    }
    deleted_ids = set()

    def check(name: str, passed: bool) -> None:
        constraints[name]["checks"] += 1
        constraints[name]["violations"] += not passed
        constraints[name]["passed"] &= passed

    start = time.perf_counter_ns()
    for index, event in enumerate(scenario["events"], 1):
        event = {**event, "source_event_id": f"{scenario['id']}:event-{index}"}
        before = target.snapshot()
        action = event["action"]
        result = getattr(target, action)(event)
        after = target.snapshot()
        item = dict(
            step=index,
            action=action,
            detail=deepcopy(event),
            result=result,
            before=before,
            after=after,
            state_diff=state_diff(before, after),
        )
        if action == "write":
            useful = event["should_retain"]
            counts["useful_proposals" if useful else "unnecessary_proposals"] += 1
            if result["retained"]:
                counts["retained"] += 1
                counts["useful_retained" if useful else "unnecessary_retained"] += 1
            fact = event["fact"]
            if (fact["tenant"], fact["user"]) != (event["tenant"], event["user"]):
                check("owner_isolation", not result["retained"] and before == after)
            if (
                fact["key"] not in ALLOWED_KEYS
                or fact["kind"] != "fact"
                or fact["source"] != "user"
            ):
                check("prohibited_writes", not result["retained"] and before == after)
        elif action == "delete":
            deleted_ids.update(result["record_ids"])
            check("deletion", not any(scope(r) == scope(event) for r in after))
        else:
            actual.append(result["answer"])
            expected.append(event["expected"])
            by_id = {r["id"]: r for r in after}
            retrieved = [by_id[key] for key in result["retrieved_ids"]]
            relevant = [
                r
                for r in retrieved
                if scope(r) == scope(event)
                and r["value"] == event["expected"]
                and valid_at(r, event["as_of"])
            ]
            counts["queries"] += 1
            counts["context_words"] += result["context_words"]
            counts["retrieved"] += len(retrieved)
            counts["distractors"] += len(retrieved) - len(relevant)
            if event["expected"] is not None:
                counts["fact_queries"] += 1
                counts["recalled"] += bool(relevant)
            if result["answer_record_id"]:
                counts["stale_answers"] += not valid_at(
                    by_id[result["answer_record_id"]], event["as_of"]
                )
            if scenario["family"] == "update":
                counts["update_queries"] += 1
                counts["correct_updates"] += result["answer"] == event["expected"]
            check(
                "owner_isolation",
                all(
                    (r["tenant"], r["user"]) == (event["tenant"], event["user"]) for r in retrieved
                ),
            )
            item.update({key: result[key] for key in ("retrieved_ids", "packed_ids", "answer")})
        if deleted_ids:
            check("deletion", not deleted_ids.intersection(r["id"] for r in after))
        trace.append(item)
    elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
    final = target.snapshot()
    success = actual == expected and all(c["passed"] for c in constraints.values())
    counts.update(
        successes=success,
        storage_records=len(final),
        storage_bytes=len(json.dumps(final, separators=(",", ":")).encode()),
    )
    return {
        **{name: scenario[name] for name in ("family", "role", "title", "description")},
        "scenario_id": scenario["id"],
        "repeat": repeat,
        "success": success,
        "expected": expected,
        "actual": actual,
        "metrics": metrics(counts, [elapsed_ms], []),
        "hard_constraints": constraints,
        "trace": trace,
        "before": [],
        "after": final,
        "state_diff": state_diff([], final),
        "counts": dict(counts),
        "latency_ms": elapsed_ms,
    }


def load_candidates(extra: dict | None = None, lineage: list[dict] | None = None) -> list[dict]:
    records = (
        deepcopy(lineage)
        if lineage is not None
        else read_json(ROOT / "experiments/candidates.json")
    )
    if not isinstance(records, list):
        raise ValueError("The frozen candidate lineage must be an array")
    if extra is not None:
        if not isinstance(extra, dict):
            raise ValueError("A submitted candidate must be a JSON object")
        records.append(extra)
    if not 1 <= len(records) <= MAX_CANDIDATES:
        raise ValueError(f"Candidate budget is 1 through {MAX_CANDIDATES}")
    configs, resolved = {}, []
    required = {"id", "label", "parent_id", "hypothesis", "predicted_effect", "patch", "proposer"}
    for record in records:
        if not isinstance(record, dict) or set(record) != required:
            raise ValueError(f"Candidate fields must be exactly {sorted(required)}")
        identifier = record["id"]
        if (
            not isinstance(identifier, str)
            or not identifier.isascii()
            or not 1 <= len(identifier) <= 64
            or not identifier.replace("-", "").isalnum()
            or identifier in configs
        ):
            raise ValueError(
                "Candidate ID must be unique ASCII letters/digits/hyphens, at most 64 characters"
            )
        parent = record["parent_id"]
        if parent is not None and parent not in configs:
            raise ValueError("Candidate parent must already exist in the resolved lineage")
        if parent is None and resolved:
            raise ValueError("Only the baseline can have no parent")
        for name in ("label", "hypothesis", "predicted_effect"):
            if not isinstance(record[name], str) or not 1 <= len(record[name]) <= 2000:
                raise ValueError(f"Invalid candidate {name}")
        proposer = record["proposer"]
        if not isinstance(proposer, dict) or not {"type", "name", "model", "prompt_version"} <= set(
            proposer
        ):
            raise ValueError(
                "Candidate needs explicit proposer type, name, model and prompt version"
            )
        if any(not isinstance(value, str) or len(value) > 2000 for value in proposer.values()):
            raise ValueError("Proposer metadata must contain bounded strings")
        previous = configs[parent] if parent else Config()
        config = previous.patch(record["patch"])
        configs[identifier] = config
        resolved.append(
            {
                **record,
                "config": asdict(config),
                "changes": [
                    {"field": key, "before": asdict(previous)[key], "after": value}
                    for key, value in asdict(config).items()
                    if value != asdict(previous)[key]
                ],
            }
        )
    return resolved


def aggregate(runs: list[dict], repeats: int) -> dict:
    counts = sum((Counter(run["counts"]) for run in runs), Counter())
    repeat_scores = [
        statistics.mean(r["success"] for r in runs if r["repeat"] == repeat)
        for repeat in range(repeats)
    ]
    constraints = {}
    for name in runs[0]["hard_constraints"]:
        checks = sum(run["hard_constraints"][name]["checks"] for run in runs)
        violations = sum(run["hard_constraints"][name]["violations"] for run in runs)
        constraints[name] = dict(passed=violations == 0, checks=checks, violations=violations)
    return dict(
        metrics=metrics(counts, [r["latency_ms"] for r in runs], repeat_scores),
        counts=dict(counts),
        repeat_count=repeats,
        task_count=len(runs) // repeats,
        hard_constraints=constraints,
    )


def git_context() -> dict:
    try:

        def git(*args):
            return subprocess.check_output(
                ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
            ).strip()

        return dict(
            commit=git("rev-parse", "HEAD"), dirty=bool(git("status", "--porcelain", "--", "."))
        )
    except (OSError, subprocess.CalledProcessError):
        return dict(commit=None, dirty=None)


def provenance() -> dict:
    paths = sorted(
        [
            *ROOT.glob("lab/*.py"),
            *ROOT.glob("tests/*.py"),
            ROOT / "data/scenarios.json",
            ROOT / "experiments/candidates.json",
            ROOT / "experiments/contract.json",
            ROOT / "pyproject.toml",
            ROOT / "uv.lock",
            ROOT / ".python-version",
        ]
    )
    files = {str(path.relative_to(ROOT)): sha256(path) for path in paths if path.exists()}
    return {
        "target_version": "structured-memory-v1",
        "evaluator_version": "exact-state-v1",
        "dataset_version": "original-synthetic-v1",
        "consumer_version": "first-key-match-v1",
        "source_sha256": hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
        "source_files": files,
        "python": sys.version,
        "platform": platform.platform(),
        "model": "none; deterministic structured target",
        "prompt": "none at runtime",
        "randomness": "none; seeds do not apply",
        "git": git_context(),
    }


def build_bundle(
    repeats: int = 1,
    extra: dict | None = None,
    parent_release: Path | None = None,
    *,
    lineage: list[dict] | None = None,
) -> tuple[dict, list[dict]]:
    if type(repeats) is not int or not 1 <= repeats <= MAX_REPEATS:
        raise ValueError(f"Repeats must be between 1 and {MAX_REPEATS}")
    scenarios = read_json(ROOT / "data/scenarios.json")
    validate_scenarios(scenarios)
    parent_manifest = verify_source(parent_release) if parent_release is not None else None
    if parent_release is not None:
        if lineage is not None:
            raise ValueError("Use a parent release or an initial lineage, not both")
        lineage = read_json(parent_release / "inputs/candidates.json")
    candidates = load_candidates(extra, lineage)
    deadline = time.monotonic() + MAX_WALL_SECONDS
    all_runs, by_id = [], {}
    for candidate in candidates:
        runs = []
        for repeat in range(repeats):
            for scenario in scenarios:
                if time.monotonic() > deadline:
                    raise TimeoutError(f"Campaign exceeded {MAX_WALL_SECONDS} seconds")
                run = run_scenario(scenario, Config(**candidate["config"]), repeat)
                run["candidate_id"] = candidate["id"]
                runs.append(run)
        summary = aggregate(runs, repeats)
        summary["role_metrics"] = {
            role: aggregate([r for r in runs if r["role"] == role], repeats)["metrics"]
            for role in ("search", "evaluation", "adversarial")
        }
        parent = by_id.get(candidate["parent_id"])
        parent_runs = parent["runs"] if parent else runs[: len(scenarios)]
        parent_success = {r["scenario_id"]: int(r["success"]) for r in parent_runs}
        differences = [
            int(r["success"]) - parent_success[r["scenario_id"]] for r in runs if r["repeat"] == 0
        ]
        repeat_deltas = [
            statistics.mean(
                int(r["success"]) - parent_success[r["scenario_id"]]
                for r in runs
                if r["repeat"] == i
            )
            for i in range(repeats)
        ]
        summary["paired"] = dict(
            parent_id=candidate["parent_id"],
            task_count=len(scenarios),
            wins=differences.count(1),
            ties=differences.count(0),
            losses=differences.count(-1),
            mean_delta=statistics.mean(differences),
            repeat_deltas=repeat_deltas,
        )
        bad_constraints = any(not c["passed"] for c in summary["hard_constraints"].values())
        delta = summary["paired"]["mean_delta"]
        if not parent:
            status, rationale = (
                "retain_baseline",
                "Frozen comparator; remaining failures are recorded.",
            )
        elif bad_constraints or delta < 0:
            status, rationale = (
                "recommend_reject",
                "A hard-constraint violation or lower downstream success blocks recommendation, even if a local metric improves.",
            )
        elif delta > 0:
            status, rationale = (
                "recommend_accept",
                "Higher downstream success on these public checks, with no hard-constraint violation. Human review is still required.",
            )
        elif (
            summary["metrics"]["storage_records"] < parent["summary"]["metrics"]["storage_records"]
        ):
            status, rationale = (
                "recommend_accept",
                "Downstream success is unchanged; duplicate removal lowers stored rows on these fixtures. This is an efficiency recommendation, not a quality gain.",
            )
        else:
            status, rationale = (
                "recommend_reject",
                "No downstream or storage benefit measured against the parent; keep the evidence and retain the simpler parent.",
            )
        candidate.update(
            summary=summary,
            runs=[r for r in runs if r["repeat"] == 0],
            budget=dict(
                repeats=repeats,
                scenario_runs=len(runs),
                max_wall_seconds=MAX_WALL_SECONDS,
                provider_calls=0,
                provider_cost_usd=0,
            ),
            recommendation=dict(status=status, rationale=rationale),
            decision=dict(
                status="pending_human_review",
                actor=None,
                rationale="No person has reviewed or authorized this candidate; recommendations are evidence for that decision.",
            ),
        )
        by_id[candidate["id"]] = candidate
        all_runs.extend(runs)
    blocked = []
    for identifier, patch in (
        ("disable-tenant-scope", {"tenant_isolation": False}),
        ("keep-deleted-history", {"delete_all_versions": False}),
        ("allow-prohibited-writes", {"allow_secrets": True}),
        ("replace-evaluator", {"evaluator": "always-pass"}),
        ("unbounded-retrieval", {"top_k": 1000000}),
    ):
        try:
            Config().patch(patch)
        except ValueError as error:
            blocked.append(
                dict(id=identifier, patch=patch, error=str(error), status="rejected_before_run")
            )
        else:
            raise AssertionError("Unsafe proposal unexpectedly passed validation")
    return {
        "schema_version": "1.0",
        "release_id": "article-01.3",
        "parent_release": (
            {
                "release_id": parent_manifest["release_id"],
                "manifest_sha256": sha256(parent_release / "manifest.json"),
            }
            if parent_manifest
            else None
        ),
        "generated_at": datetime.now(UTC).isoformat(),
        "disclosures": [
            "Synthetic public fixtures",
            "Artifact-first; no live model calls",
            "Human review pending",
        ],
        "limitations": LIMITATIONS,
        "provenance": provenance(),
        "reproduction_command": "uv run --frozen python -m lab run",
        "links": {"article": None, "source": None, "release": None},
        "metric_definitions": {
            key: dict(zip(("label", "unit", "description", "direction"), value, strict=True))
            for key, value in METRICS.items()
        },
        "scenarios": [
            {key: s[key] for key in ("id", "family", "role", "title", "description")}
            for s in scenarios
        ],
        "candidates": candidates,
        "blocked_proposals": blocked,
    }, all_runs


def format_metric(value, unit: str) -> str:
    if value is None:
        return "n/a"
    if unit == "fraction":
        return f"{value:.1%}"
    return f"{value:.4f}" if unit == "ms" else f"{value:.2f}"


def write_reports(output: Path, bundle: dict) -> None:
    candidates = bundle["candidates"]
    labels = [c["label"] for c in candidates]
    rows = []
    for key, definition in bundle["metric_definitions"].items():
        if key == "success_repeat_stddev" and all(
            c["summary"]["repeat_count"] == 1 for c in candidates
        ):
            continue
        rows.append(
            [definition["label"] + f" ({definition['unit']})"]
            + [format_metric(c["summary"]["metrics"][key], definition["unit"]) for c in candidates]
        )
    lines = [
        "# Memory improvement loop — measured evidence",
        "",
        "Original synthetic data; deterministic execution; all candidate decisions await human review.",
        "",
        f"Release: `{bundle['release_id']}`. Source SHA-256: `{bundle['provenance']['source_sha256']}`.",
        "",
        "| Metric | " + " | ".join(labels) + " |",
        "| --- | " + " | ".join("---:" for _ in labels) + " |",
    ]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    for candidate in candidates:
        paired = candidate["summary"]["paired"]
        lines += [
            "",
            f"## {candidate['label']}",
            "",
            candidate["hypothesis"],
            "",
            f"Patch: `{json.dumps(candidate['patch'], sort_keys=True)}`. Parent: `{candidate['parent_id']}`.",
            "",
            f"Recommendation: **{candidate['recommendation']['status']}** — {candidate['recommendation']['rationale']}",
            "",
            "Decision: **pending human review**. No candidate has been promoted.",
            "",
            f"Paired with parent: {paired['wins']} wins, {paired['ties']} ties, {paired['losses']} losses across {paired['task_count']} scenarios.",
            "",
            "Hard constraints: "
            + "; ".join(
                f"{name}: {item['violations']}/{item['checks']} violations"
                for name, item in candidate["summary"]["hard_constraints"].items()
            )
            + ".",
            "",
            "Failed scenarios: "
            + (", ".join(r["scenario_id"] for r in candidate["runs"] if not r["success"]) or "none")
            + ".",
        ]
    lines += [
        "",
        "## Interpretation",
        "",
        "Scoped history bundles entity filtering and time validity. Deduplication is neutral on downstream answers and reduces duplicate storage. Lowering the write threshold recovers one useful low-confidence fact, but also retains uncertain conflicts: a useful-write-recall win can accompany a downstream regression.",
        "",
        "Counts and denominators are in each candidate's summary.counts and per-run counts. Role metrics are reported separately in bundle.json; none is held out from authorship.",
        "",
        "## Reproduce and verify",
        "",
        "```sh",
        bundle["reproduction_command"],
        f"uv run --frozen python -m lab verify {output.as_posix() if not output.is_relative_to(ROOT) else output.relative_to(ROOT)}",
        "```",
        "",
        "## Limits",
        "",
    ] + [f"- {text}" for text in LIMITATIONS]
    (output / "report.md").write_text("\n".join(lines) + "\n")
    esc = html.escape
    table = (
        "<table><caption>Measured comparison across public synthetic scenarios</caption><thead><tr><th scope='col'>Metric</th>"
        + "".join(f"<th scope='col'>{esc(label)}</th>" for label in labels)
        + "</tr></thead><tbody>"
    )
    for row in rows:
        table += (
            f"<tr><th scope='row'>{esc(row[0])}</th>"
            + "".join(f"<td>{esc(cell)}</td>" for cell in row[1:])
            + "</tr>"
        )
    table += "</tbody></table>"
    decisions = "".join(
        f"<section><h2>{esc(c['label'])}</h2><p>{esc(c['hypothesis'])}</p><p><strong>{esc(c['recommendation']['status'])}</strong>: {esc(c['recommendation']['rationale'])}</p><p>Decision: pending human review. No candidate has been promoted.</p></section>"
        for c in candidates
    )
    document = (
        "<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Memory loop evidence report</title><style>body{font:16px/1.6 system-ui,sans-serif;color:#17263a;background:#f9fbff;max-width:1100px;margin:auto;padding:24px}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:10px;border-bottom:1px solid #ccd4df}td{font-variant-numeric:tabular-nums}caption{text-align:left;font-weight:700;margin:12px 0}.table-scroll{overflow-x:auto}code{overflow-wrap:anywhere}a{color:#1357aa}</style><body><h1>Memory improvement loop</h1><p>Original synthetic data. Deterministic replay. All candidate decisions await human review.</p><div class='table-scroll' tabindex='0' role='region' aria-label='Comparison table'>"
        + table
        + "</div>"
        + decisions
        + "<h2>Limits</h2><ul>"
        + "".join(f"<li>{esc(text)}</li>" for text in LIMITATIONS)
        + "</ul><h2>Run locally</h2><pre><code>"
        + esc(bundle["reproduction_command"])
        + "</code></pre><p><a href='bundle.json'>Complete evidence JSON</a> · <a href='manifest.json'>File hashes and versions</a> · <a href='report.md'>Markdown report</a></p></body></html>"
    )
    (output / "report.html").write_text(document)


def export(output: Path, bundle: dict, all_runs: list[dict]) -> None:
    if (
        len((json.dumps(bundle, indent=2, ensure_ascii=False) + "\n").encode())
        > MAX_ARTIFACT_JSON_BYTES
    ):
        raise ValueError("Bundle exceeds the 64 MB artifact JSON budget")
    # Exclusive creation preserves every frozen release; corrections use a new directory.
    output.mkdir(parents=True, exist_ok=False)
    dump(output / "bundle.json", bundle)
    for name, values in (
        ("candidates", [{k: v for k, v in c.items() if k != "runs"} for c in bundle["candidates"]]),
        ("runs", all_runs),
    ):
        (output / f"{name}.jsonl").write_text(
            "".join(
                json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n" for value in values
            )
        )
    dump(output / "metrics.json", {c["id"]: c["summary"] for c in bundle["candidates"]})
    dump(output / "inputs/scenarios.json", read_json(ROOT / "data/scenarios.json"))
    dump(
        output / "inputs/candidates.json",
        [
            {
                k: c[k]
                for k in (
                    "id",
                    "label",
                    "parent_id",
                    "hypothesis",
                    "predicted_effect",
                    "patch",
                    "proposer",
                )
            }
            for c in bundle["candidates"]
        ],
    )
    for candidate in bundle["candidates"]:
        for run in candidate["runs"]:
            name = f"{candidate['id']}/{run['scenario_id']}.json"
            dump(output / "traces" / name, run["trace"])
            dump(output / "state-diffs" / name, run["state_diff"])
    write_reports(output, bundle)
    manifest = {
        key: bundle[key]
        for key in ("schema_version", "release_id", "generated_at", "provenance", "limitations")
    }
    manifest.update(
        lab_id="memory-improvement",
        article=1,
        interaction_tier="artifact-first",
        synthetic=True,
        entrypoints=dict(explorer="bundle.json", report="report.html", runs="runs.jsonl"),
        files=[
            dict(path=str(path.relative_to(output)), sha256=sha256(path))
            for path in sorted(output.rglob("*"))
            if path.is_file()
        ],
    )
    dump(output / "manifest.json", manifest)


def verify(output: Path) -> int:
    if any(path.is_symlink() for path in output.rglob("*")):
        raise ValueError(
            "Artifact releases must contain ordinary files and directories, not symlinks"
        )
    manifest = read_json(output / "manifest.json")
    expected = set()
    for item in manifest["files"]:
        path = output / item["path"]
        if not path.resolve().is_relative_to(output.resolve()):
            raise ValueError("Manifest file path escapes the artifact directory")
        if not path.is_file() or sha256(path) != item["sha256"]:
            raise ValueError(f"Artifact hash mismatch: {item['path']}")
        expected.add(item["path"])
    actual = {str(p.relative_to(output)) for p in output.rglob("*") if p.is_file()} - {
        "manifest.json"
    }
    if actual != expected:
        raise ValueError("Artifact inventory does not match the manifest")
    return len(expected)


def verify_source(output: Path) -> dict:
    """A descendant reuses the same engine, evaluator, fixtures and contract as its parent."""
    verify(output)
    manifest = read_json(output / "manifest.json")
    if manifest["provenance"]["source_files"] != provenance()["source_files"]:
        raise ValueError(
            "Current source differs from the parent release; run a new baseline before extending it"
        )
    return manifest


def read_bundle(output: Path, *, current_source: bool = False) -> dict:
    if current_source:
        verify_source(output)
    else:
        verify(output)
    return read_json(output / "bundle.json", max_bytes=MAX_ARTIFACT_JSON_BYTES)
