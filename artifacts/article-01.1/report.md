# Memory improvement loop — measured evidence

Original synthetic data; deterministic execution; all candidate decisions await human review.

Release: `article-01.1`. Source SHA-256: `d6182dfb83dcd2fe79d6dbe790dd457df8762f4781dabbcc810e5d047a5ef4ea`.

| Metric | Baseline | Scoped history | Deduplicate confirmations | Write more |
| --- | ---: | ---: | ---: | ---: |
| Downstream success (fraction) | 65.0% | 95.0% | 95.0% | 80.0% |
| Useful-write precision (fraction) | 100.0% | 100.0% | 100.0% | 90.5% |
| Useful-write recall (fraction) | 97.4% | 97.4% | 97.4% | 100.0% |
| Unnecessary-write rate (fraction) | 0.0% | 0.0% | 0.0% | 57.1% |
| Relevant-memory recall (fraction) | 90.5% | 95.2% | 95.2% | 85.7% |
| Distracting-memory rate (fraction) | 48.6% | 4.8% | 4.8% | 21.7% |
| Stale/future fact rate (fraction) | 14.8% | 0.0% | 0.0% | 0.0% |
| Update correctness (fraction) | 100.0% | 100.0% | 100.0% | 100.0% |
| Mean context words (words) | 4.11 | 2.33 | 2.33 | 2.56 |
| Mean stored records (records) | 1.70 | 1.70 | 1.60 | 1.95 |
| Mean stored bytes (bytes) | 416.35 | 416.35 | 390.45 | 479.05 |
| Local p50 latency (ms) | 0.0459 | 0.0433 | 0.0432 | 0.0435 |
| Local p95 latency (ms) | 0.2886 | 0.2307 | 0.2450 | 0.1754 |
| Provider expenditure (USD) | 0.00 | 0.00 | 0.00 | 0.00 |
| Model tokens (tokens) | 0.00 | 0.00 | 0.00 | 0.00 |
| Repeat success stddev (fraction) | 0.0% | 0.0% | 0.0% | 0.0% |

## Baseline

Freeze the original thresholded writer and recency-based retrieval.

Patch: `{}`. Parent: `None`.

Recommendation: **retain_baseline** — Frozen comparator; remaining failures are recorded.

Decision: **pending human review**. No candidate has been promoted.

Paired with parent: 0 wins, 20 ties, 0 losses across 20 scenarios. Repeat deltas: [0, 0, 0].

Hard constraints: owner_isolation: 0/84 violations; deletion: 0/33 violations; prohibited_writes: 0/6 violations.

Failed scenarios: entity-grounding, historical-address, future-move, distractor-retrieval, selective-deletion, useful-low-confidence, history-boundary.

## Scoped history

Filter by the requested entity and the fact validity interval before ranking.

Patch: `{"filter_entity": true, "time_aware": true}`. Parent: `baseline`.

Recommendation: **recommend_accept** — Higher downstream success on these public checks, with no hard-constraint violation. Human review is still required.

Decision: **pending human review**. No candidate has been promoted.

Paired with parent: 6 wins, 14 ties, 0 losses across 20 scenarios. Repeat deltas: [0.3, 0.3, 0.3].

Hard constraints: owner_isolation: 0/84 violations; deletion: 0/33 violations; prohibited_writes: 0/6 violations.

Failed scenarios: useful-low-confidence.

## Deduplicate confirmations

Repeated identical active facts do not need another version.

Patch: `{"deduplicate": true}`. Parent: `scoped-history`.

Recommendation: **recommend_accept** — Downstream success is unchanged; duplicate removal lowers stored rows on these fixtures. This is an efficiency recommendation, not a quality gain.

Decision: **pending human review**. No candidate has been promoted.

Paired with parent: 0 wins, 20 ties, 0 losses across 20 scenarios. Repeat deltas: [0, 0, 0].

Hard constraints: owner_isolation: 0/84 violations; deletion: 0/33 violations; prohibited_writes: 0/6 violations.

Failed scenarios: useful-low-confidence.

## Write more

Lowering the admission threshold should retain more useful proposals.

Patch: `{"min_confidence": 0.2}`. Parent: `scoped-history`.

Recommendation: **recommend_reject** — A hard-constraint violation or lower downstream success blocks recommendation, even if a local metric improves.

Decision: **pending human review**. No candidate has been promoted.

Paired with parent: 1 wins, 15 ties, 4 losses across 20 scenarios. Repeat deltas: [-0.15, -0.15, -0.15].

Hard constraints: owner_isolation: 0/84 violations; deletion: 0/33 violations; prohibited_writes: 0/6 violations.

Failed scenarios: unnecessary-write, uncertain-conflict, uncertain-timezone, clean-abstention.

## Interpretation

Scoped history bundles entity filtering and time validity. Deduplication is neutral on downstream answers and reduces duplicate storage. Lowering the write threshold recovers one useful low-confidence fact, but also retains uncertain conflicts: a useful-write-recall win can accompany a downstream regression.

Counts and denominators are in each candidate's summary.counts and per-run counts. Role metrics are reported separately in bundle.json; none is held out from authorship.

## Reproduce and verify

```sh
uv run --frozen python -m lab run
uv run --frozen python -m lab verify artifacts/article-01.1
```

## Limits

- All scenarios are original synthetic public fixtures visible during candidate authorship. Search/evaluation/adversarial roles are regression and validation organization, not blind held-out sets.
- This target starts from structured fact proposals. Confidence scores are hand-authored fixture values, not calibrated probabilities. It does not measure language extraction, model calibration, or a real assistant's reasoning.
- The frozen consumer returns the first packed fact with the requested key. Its failure modes are inspectable; they do not estimate a language model's behavior.
- Scoped history changes entity and temporal filtering together. Its gain is attributable to the tested bundle; this run does not estimate the isolated effect of each switch.
- Repeated runs are identical deterministic tasks in isolated memory. Zero score variance checks replay consistency; it is not a confidence interval or evidence of generalization.
- Configuration validation limits what these manifests can change. This same-user process is not an operating-system sandbox against a malicious coding agent with filesystem access.
- The durable-key/source/kind gate rejects the supplied structured attacks. It is not a general prompt-injection defense or a detector for secrets hidden in allowed values.
- Latency is local execution of tiny in-memory scenarios. Context words are not model tokens. Zero provider expenditure excludes authoring, machine and electricity costs.
- Recommendations await human review. No production change, real human approval, repository publication, or deployment has occurred.
