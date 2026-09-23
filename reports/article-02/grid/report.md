# Part 2: answer-only selection against the full evaluator

Original synthetic fixtures written with knowledge of the candidates. Audit cases are withheld from the selector, not from the authors. All cases are public.

**Answer-only selection picks `threshold-0.2-k1`.** 2 of 8 candidates pass every check: `threshold-0.6-k1`, `threshold-0.6-k3`. **Decision: keep the incumbent threshold-0.6-k3.**

Runs: 1600 (8 candidates × 40 scenarios × 5 fresh-state sweeps). Model calls: 0. All sweeps gave the same answers, state checks and hard-constraint checks; only local timing differs.

## Candidates

| Candidate | Development answers | Unwanted writes (dev / audit / previous) | Audit answers | Previous suite | Context words (dev / audit / previous) | Failed checks |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `threshold-0.2-k1` | 8/8 | 4 / 6 / 4 | 6/12 | 16/20 | 3.00 / 3.00 / 2.56 | unwanted development writes; audit answers below 100%; unwanted audit writes; previous suite failed; unwanted previous-suite writes |
| `threshold-0.2-k3` | 8/8 | 4 / 6 / 4 | 6/12 | 16/20 | 4.50 / 3.00 / 2.56 | unwanted development writes; audit answers below 100%; unwanted audit writes; previous suite failed; unwanted previous-suite writes; development context budget exceeded |
| `threshold-0.4-k1` | 8/8 | 0 / 6 / 1 | 6/12 | 19/20 | 3.00 / 3.00 / 2.44 | audit answers below 100%; unwanted audit writes; previous suite failed; unwanted previous-suite writes |
| `threshold-0.4-k3` | 8/8 | 0 / 6 / 1 | 6/12 | 19/20 | 3.00 / 3.00 / 2.44 | audit answers below 100%; unwanted audit writes; previous suite failed; unwanted previous-suite writes |
| `threshold-0.6-k1` | 6/8 | 0 / 0 / 0 | 12/12 | 20/20 | 2.25 / 3.00 / 2.44 | none |
| `threshold-0.6-k3` (incumbent) | 6/8 | 0 / 0 / 0 | 12/12 | 20/20 | 2.25 / 3.00 / 2.44 | none |
| `threshold-0.7-k1` | 6/8 | 0 / 0 / 0 | 6/12 | 19/20 | 2.25 / 1.50 / 2.33 | audit answers below 100%; previous suite failed |
| `threshold-0.7-k3` | 6/8 | 0 / 0 / 0 | 6/12 | 19/20 | 2.25 / 1.50 / 2.33 | audit answers below 100%; previous suite failed |

Previous suite uses the Part 1 definition of success: every answer correct and every hard-constraint check passing. Context words are whitespace-separated words, not model tokens; the budget is 3 per query. The local p95 budget is 10 ms per scenario; every candidate is under it in this run. Timings vary between runs and are in `bundle.json`.

## First candidate that passes each evidence layer

| Evidence | First passing candidate |
| --- | --- |
| Answers only | `threshold-0.2-k1` |
| + development state checks | `threshold-0.4-k1` |
| + audit cases | `threshold-0.6-k1` |
| + previous suite and hard constraints | `threshold-0.6-k1` |
| + context and latency budgets | `threshold-0.6-k1` |

Ties keep the declared candidate order. Passing a layer only makes a candidate eligible; the adoption rule below decides whether it replaces the incumbent.

## Adoption decision

Adopt a challenger only if it passes every check and, compared scenario by scenario with the incumbent, it wins at least one scenario and loses none. Otherwise keep the incumbent.

- `threshold-0.6-k1` passes every check: 0 wins and 0 losses against the incumbent across 40 scenarios.
- Outcome: **keep the incumbent threshold-0.6-k3**.

## Paired comparison with the incumbent

Each cell is wins-losses-ties against the incumbent on the same scenarios. The 8 development cases come from 3 templates and the 12 audit cases from 2 templates, so cases within a template are not independent samples.

| Candidate | development: unrelated-guess | development: confirmed-only | development: useful-0.4-preference | audit: uncertain-city-update | audit: useful-0.6-preference | previous-suite: Part 1 scenarios |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `threshold-0.2-k1` | 0-0-4 | 0-0-2 | 2-0-0 | 0-6-0 | 0-0-6 | 0-4-16 |
| `threshold-0.2-k3` | 0-0-4 | 0-0-2 | 2-0-0 | 0-6-0 | 0-0-6 | 0-4-16 |
| `threshold-0.4-k1` | 0-0-4 | 0-0-2 | 2-0-0 | 0-6-0 | 0-0-6 | 0-1-19 |
| `threshold-0.4-k3` | 0-0-4 | 0-0-2 | 2-0-0 | 0-6-0 | 0-0-6 | 0-1-19 |
| `threshold-0.6-k1` | 0-0-4 | 0-0-2 | 0-0-2 | 0-0-6 | 0-0-6 | 0-0-20 |
| `threshold-0.6-k3` | 0-0-4 | 0-0-2 | 0-0-2 | 0-0-6 | 0-0-6 | 0-0-20 |
| `threshold-0.7-k1` | 0-0-4 | 0-0-2 | 0-0-2 | 0-0-6 | 0-6-0 | 0-1-19 |
| `threshold-0.7-k3` | 0-0-4 | 0-0-2 | 0-0-2 | 0-0-6 | 0-6-0 | 0-1-19 |

## Pareto frontier

Among candidates that pass the previous-suite layer, a candidate is on the frontier if no other candidate has at least its audit answer success and at most its audit context words, and is strictly better on one. Frontier: `threshold-0.6-k1`, `threshold-0.6-k3`.

## Limits

- The audit cases were written by the author who knew the eight candidates. They are hidden from the selector, not a blind test.
- A correct answer can still hide a bad write; the state check depends on the `should_retain` label in each fixture being right.
- The deterministic target makes no model calls, so this run measures no judge, calibration or model variance. The Jev comparison is in `../jev/report.md`.

## Reproduce

```sh
uv run --frozen python -m lab.evaluator_exploits --output artifacts/my-evaluator-study
uv run --frozen python -m lab verify artifacts/my-evaluator-study
```
