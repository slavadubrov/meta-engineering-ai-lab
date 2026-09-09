# Memory improvement loop — measured evidence

Original synthetic data; deterministic execution; all candidate decisions await human review.

Release: `evaluation`. Source SHA-256: `961aa593955873e4cfae672fb56286e599f587cc2ebdcca57f0bb6ffd709649f`.

| Metric | Baseline | Agent proposal 1 |
| --- | ---: | ---: |
| Downstream success (fraction) | 65.0% | 95.0% |
| Useful-write precision (fraction) | 100.0% | 100.0% |
| Useful-write recall (fraction) | 97.4% | 97.4% |
| Unnecessary-write rate (fraction) | 0.0% | 0.0% |
| Relevant-memory recall (fraction) | 90.5% | 95.2% |
| Distracting-memory rate (fraction) | 48.6% | 4.8% |
| Stale/future fact rate (fraction) | 14.8% | 0.0% |
| Update correctness (fraction) | 100.0% | 100.0% |
| Mean context words (words) | 4.11 | 2.33 |
| Mean stored records (records) | 1.70 | 1.70 |
| Mean stored bytes (bytes) | 416.35 | 416.35 |
| Local p50 latency (ms) | 0.0473 | 0.0465 |
| Local p95 latency (ms) | 0.2117 | 0.2948 |
| Provider expenditure (USD) | 0.00 | 0.00 |
| Model tokens (tokens) | 0.00 | 0.00 |

## Baseline

Freeze the original thresholded writer and recency-based retrieval.

Patch: `{}`. Parent: `None`.

Recommendation: **retain_baseline** — Frozen comparator; remaining failures are recorded.

Decision: **pending human review**. No candidate has been promoted.

Paired with parent: 0 wins, 20 ties, 0 losses across 20 scenarios.

Hard constraints: owner_isolation: 0/28 violations; deletion: 0/11 violations; prohibited_writes: 0/2 violations.

Failed scenarios: entity-grounding, historical-address, future-move, distractor-retrieval, selective-deletion, useful-low-confidence, history-boundary.

## Agent proposal 1

Enabling entity filtering will exclude same-key records belonging to other entities, while time-aware filtering will restrict results to records valid at the requested as-of date; together these should correct the observed grounding, historical, and future-date failures without changing writes or hard constraints.

Patch: `{"filter_entity": true, "time_aware": true}`. Parent: `baseline`.

Recommendation: **recommend_accept** — Higher downstream success on these public checks, with no hard-constraint violation. Human review is still required.

Decision: **pending human review**. No candidate has been promoted.

Paired with parent: 6 wins, 14 ties, 0 losses across 20 scenarios.

Hard constraints: owner_isolation: 0/28 violations; deletion: 0/11 violations; prohibited_writes: 0/2 violations.

Failed scenarios: useful-low-confidence.

## Interpretation

Scoped history bundles entity filtering and time validity. Deduplication is neutral on downstream answers and reduces duplicate storage. Lowering the write threshold recovers one useful low-confidence fact, but also retains uncertain conflicts: a useful-write-recall win can accompany a downstream regression.

Counts and denominators are in each candidate's summary.counts and per-run counts. Role metrics are reported separately in bundle.json; none is held out from authorship.

## Reproduce and verify

```sh
uv run --frozen python -m lab run
uv run --frozen python -m lab verify artifacts/agent-study-02/campaign-01/iteration-01/evaluation
```

## Limits

- All scenarios are original synthetic public fixtures visible during candidate authorship. Search/evaluation/adversarial roles are regression and validation organization, not blind held-out sets.
- This target starts from structured fact proposals. Confidence scores are hand-authored fixture values, not calibrated probabilities. It does not measure language extraction, model calibration, or a real assistant's reasoning.
- The frozen consumer returns the first packed fact with the requested key. Its failure modes are inspectable; they do not estimate a language model's behavior.
- Scoped history changes entity and temporal filtering together. Its gain is attributable to the tested bundle; this run does not estimate the isolated effect of each switch.
- Each scenario runs once by default. Repeating these deterministic rules adds no answer-quality evidence; variation across repeats is unavailable for a single run.
- Configuration validation limits what these manifests can change. This same-user process is not an operating-system sandbox against a malicious coding agent with filesystem access.
- The durable-key/source/kind gate rejects the supplied structured attacks. It is not a general prompt-injection defense or a detector for secrets hidden in allowed values.
- Latency is local execution of tiny in-memory scenarios. Context words are not model tokens. Zero provider expenditure excludes authoring, machine and electricity costs.
- Recommendations require human review. Running an experiment does not grant approval, change production, publish a repository, or deploy a service.
