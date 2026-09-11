# Memory improvement loop — measured evidence

Original synthetic data; deterministic execution; all candidate decisions await human review.

Release: `evaluation`. Source SHA-256: `e29a92de7497dff9e97d07de7aba37ebf30c26f9d7c55ec8f515dced8ce0418a`.

| Metric | Baseline | Agent proposal 1 | Agent proposal 2 | Agent proposal 3 |
| --- | ---: | ---: | ---: | ---: |
| Downstream success (fraction) | 65.0% | 95.0% | 95.0% | 100.0% |
| Useful-write precision (fraction) | 100.0% | 100.0% | 100.0% | 100.0% |
| Useful-write recall (fraction) | 97.4% | 97.4% | 97.4% | 100.0% |
| Unnecessary-write rate (fraction) | 0.0% | 0.0% | 0.0% | 0.0% |
| Relevant-memory recall (fraction) | 90.5% | 95.2% | 95.2% | 100.0% |
| Distracting-memory rate (fraction) | 48.6% | 4.8% | 4.8% | 4.5% |
| Stale/future fact rate (fraction) | 14.8% | 0.0% | 0.0% | 0.0% |
| Update correctness (fraction) | 100.0% | 100.0% | 100.0% | 100.0% |
| Mean context words (words) | 4.11 | 2.33 | 2.33 | 2.44 |
| Mean stored records (records) | 1.70 | 1.70 | 1.60 | 1.65 |
| Mean stored bytes (bytes) | 532.55 | 532.55 | 499.65 | 515.65 |
| Local p50 latency (ms) | 0.0665 | 0.0677 | 0.0728 | 0.0697 |
| Local p95 latency (ms) | 0.2185 | 0.2349 | 0.2459 | 0.3449 |
| Provider expenditure (USD) | 0.00 | 0.00 | 0.00 | 0.00 |
| Model tokens (tokens) | 0.00 | 0.00 | 0.00 | 0.00 |

## Baseline

Freeze the original thresholded writer and recency-based retrieval.

Patch: `{}`. Parent: `None`.

Recommendation: **retain_baseline** — Frozen comparator; remaining failures are recorded.

Decision: **pending human review**. No candidate has been promoted.

Paired with parent: 0 wins, 20 ties, 0 losses across 20 scenarios.

Hard constraints: owner_isolation: 0/28 violations; deletion: 0/11 violations; prohibited_writes: 0/2 violations.

Failed scenarios: entity-grounding, historical-address, future-move, distractor-retrieval, selective-deletion, useful-low-confidence, history-boundary.

## Agent proposal 1

Enabling entity filtering and time-aware retrieval will select the requested subject and validity interval before ranking, correcting entity distractor and historical/future-date failures without changing writes or hard-constraint behavior.

Patch: `{"filter_entity": true, "time_aware": true}`. Parent: `baseline`.

Recommendation: **recommend_accept** — Higher downstream success on these public checks, with no hard-constraint violation. Human review is still required.

Decision: **pending human review**. No candidate has been promoted.

Paired with parent: 6 wins, 14 ties, 0 losses across 20 scenarios.

Hard constraints: owner_isolation: 0/28 violations; deletion: 0/11 violations; prohibited_writes: 0/2 violations.

Failed scenarios: useful-low-confidence.

## Agent proposal 2

Enabling deduplication will reuse identical active values confirmed at later effective dates, reducing redundant storage without changing retrieval correctness.

Patch: `{"deduplicate": true}`. Parent: `agent-01`.

Recommendation: **recommend_accept** — Downstream success is unchanged; duplicate removal lowers stored rows on these fixtures. This is an efficiency recommendation, not a quality gain.

Decision: **pending human review**. No candidate has been promoted.

Paired with parent: 0 wins, 20 ties, 0 losses across 20 scenarios.

Hard constraints: owner_isolation: 0/28 violations; deletion: 0/11 violations; prohibited_writes: 0/2 violations.

Failed scenarios: useful-low-confidence.

## Agent proposal 3

Lowering min_confidence from 0.7 to 0.6 will admit the useful borderline-confidence fact while continuing to reject the lower-confidence unnecessary and conflicting writes shown in the evidence.

Patch: `{"min_confidence": 0.6}`. Parent: `agent-02`.

Recommendation: **recommend_accept** — Higher downstream success on these public checks, with no hard-constraint violation. Human review is still required.

Decision: **pending human review**. No candidate has been promoted.

Paired with parent: 1 wins, 19 ties, 0 losses across 20 scenarios.

Hard constraints: owner_isolation: 0/28 violations; deletion: 0/11 violations; prohibited_writes: 0/2 violations.

Failed scenarios: none.

## Interpretation

Scoped history bundles entity filtering and time validity. Deduplication is neutral on downstream answers and reduces duplicate storage. Lowering the write threshold recovers one useful low-confidence fact, but also retains uncertain conflicts: a useful-write-recall win can accompany a downstream regression.

Counts and denominators are in each candidate's summary.counts and per-run counts. Role metrics are reported separately in bundle.json; none is held out from authorship.

## Reproduce and verify

```sh
uv run --frozen python -m lab run
uv run --frozen python -m lab verify artifacts/agent-study-03/campaign-01/iteration-03/evaluation
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
