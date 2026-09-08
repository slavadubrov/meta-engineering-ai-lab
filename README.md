# Closed-Loop AI Lab

A small, runnable memory experiment: turn a recorded failure into a bounded
configuration change, rerun the target, inspect the evidence, and leave the
promotion decision to a person.

The Python engine produces the results. A plain JavaScript explorer displays
the frozen artifacts. There is no model key, runtime API bill, database, build
step, or application server.

Source: [slavadubrov/closed-loop-ai-lab](https://github.com/slavadubrov/closed-loop-ai-lab).
The companion article remains an unpublished draft. The repository and its
frozen experiment are available independently of article publication.

## Run it

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run:

```sh
git clone https://github.com/slavadubrov/closed-loop-ai-lab.git
cd closed-loop-ai-lab
uv run --frozen python -m lab run
```

The command runs the baseline plus three candidates, each on 20 independent
synthetic scenarios three times. It creates a new `artifacts/local-<timestamp>/`
directory containing a complete report, metrics, traces, state diffs, input
snapshots, and a SHA-256 manifest. It never overwrites another run.

Python 3.12+ is required; uv can provision the interpreter. The first setup
downloads the pinned Ruff development tool. After setup, the experiment itself
uses only the standard library and performs no network calls. To omit developer
tools, use `uv run --frozen --no-dev python -m lab run`.

Open the **frozen article evidence** in the local explorer:

```sh
uv run --frozen python -m lab serve
```

Visit [http://127.0.0.1:8000/web/](http://127.0.0.1:8000/web/). It serves on
loopback only. The explorer initially uses `artifacts/article-01.2/`, the exact
evidence packaged with the draft. Fresh runs keep their own directories; open
their `report.html` through the same server to inspect their results. Stop the
server with Ctrl+C.

## What the experiment actually does

The target receives **structured fact proposals**, such as an account city and
its effective date. Their confidence values are hand-authored fixture scores,
not calibrated model probabilities. This deliberately starts after natural
language extraction. A frozen consumer returns the first packed record with
the requested key; it makes retrieval failures easy to inspect.

For example, a user reports a move to Paris on January 3, effective January 10.
On January 5, the baseline retrieves the newest report and answers Paris.
The history candidate filters by the requested entity and the validity interval,
so it answers Berlin. Both versions retain the same underlying history.

| Candidate | Change from parent | Observed downstream success | Interpretation |
| --- | --- | ---: | --- |
| `baseline` | Frozen initial configuration | 13/20 | Comparator with recorded failures |
| `scoped-history` | Entity and validity filters | 19/20 | Six recovered scenarios; two switches tested together |
| `deduplicated` | Deduplicate identical active confirmations | 19/20 | Neutral answers, lower stored row count |
| `broad-writes` | Confidence threshold 0.7 → 0.2 | 16/20 | Useful-write recall improves, but four uncertain writes cause failures |

The broader writer improves useful-write recall from 37/38 to 38/38 while
downstream success falls from 19/20 to 16/20 relative to its parent. Local
metrics and downstream outcomes answer different questions. See the generated
[evidence report](artifacts/article-01.2/report.md) for denominators, timing,
storage, context size, constraint checks, and paired comparisons.

All original candidates were authored by **Codex during development**, with
access to the public fixtures. The engine does not fabricate human-authored
baselines, model calls, or completed human review. Every promotion decision is
`pending_human_review`; accept/reject recommendations are not authorizations.

## Run the improvement loop

Export actual baseline failures and metrics from the search role:

```sh
uv run --frozen python -m lab packet \
  --release artifacts/article-01.2 --output proposal-packet.json
```

The packet contains the current configuration, mutable surface, source hashes,
and complete failed search traces. Give it to a coding agent, or inspect it
yourself, and return a candidate manifest with the exact fields demonstrated in
`experiments/candidates.json`. Keep its proposer attribution truthful.

For a fully local demonstration, two deterministic diagnosis rules inspect the
wrong-answer record: wrong entity enables entity filtering; invalid date enables
temporal filtering. They generate a new candidate from the actual trace:

```sh
uv run --frozen python -m lab propose \
  --release artifacts/article-01.2 --output diagnosed-candidate.json
uv run --frozen python -m lab evaluate \
  --release artifacts/article-01.2 --candidate diagnosed-candidate.json
```

This is a working failure → diagnosis → candidate → evaluation loop. The
diagnoser is explicitly **rule based**, not an LLM researcher. `evaluate` also
accepts other valid patches within the same surface. It evaluates the supplied
candidate alongside the original lineage and records its manifest in the new
release. For the next generation, export a packet with `--release` pointing to
that new directory and `--parent` naming the new candidate. Pass the same release
to `evaluate --release` when testing its child. The evaluator imports the frozen
lineage, preserves each ancestor's proposer record, and records the parent
manifest hash. Source, fixture, contract, and lockfile hashes must match before
the lineage can be extended; changed code or data require a new baseline.
The campaign is bounded to eight candidates including ancestors. Output files
are created exclusively; choose a new path to repeat an export.

The configuration surface is limited to `min_confidence`, `filter_entity`,
`time_aware`, `deduplicate`, and `top_k`. Their types and ranges are checked
before execution. Unknown fields, non-finite thresholds, out-of-budget runs,
and attempts to disable owner isolation, deletion, or prohibited-write rules
are rejected. `experiments/contract.json` documents the boundary. Each scenario
starts with new in-memory state; no candidate source code is loaded or executed.

When **you** have reviewed a candidate, this optional command records your
decision separately from the frozen evidence:

```sh
uv run --frozen python -m lab decision \
  --release artifacts/article-01.2 --candidate scoped-history \
  --verdict accept --reviewer "Your name" --reason "Your evidence-based rationale"
```

Use `--verdict reject` for rejection. These are explicit operator declarations,
not independently authenticated identities. The command only appends a review
record under `decisions/`; it never deploys, changes the running target, or
rewrites the original bundle. The browser's decision rehearsal is a local
simulation and does not invoke this command.

## Verify it

```sh
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen ruff check lab tests
uv run --frozen ruff format --check lab tests
uv run --frozen python -m lab verify artifacts/article-01.2 --source
```

Tests cover the observed positive/neutral/regressing outcomes, owner isolation,
deletion and fresh consent, prohibited writes, canonical dates and validity
boundaries, proposal validation and run limits, repeat consistency, frozen-file
integrity, and trace-driven candidate generation. The suite also checks two
generations through the CLI, feedback export at the eight-candidate budget,
source drift, and rejection of a null candidate before output creation.
`verify` checks the artifact
inventory and content hashes; `--source` also compares the current Python,
fixtures, manifests, and lockfile to recorded source hashes. Hashes detect
accidental changes relative to the manifest; they are not a digital signature
against someone who can replace both data and manifest.

Optional browser smoke coverage lives in `web/smoke.mjs`. Install its test-only
dependency in this directory, keep the local server running, then run:

```sh
npm install --no-save --package-lock=false puppeteer
node web/smoke.mjs http://127.0.0.1:8000/web/
```

If using an existing Chrome installation, set `PUPPETEER_EXECUTABLE_PATH` to its
executable. Running the actual frontend needs no npm dependency. See
[deployment instructions](DEPLOYMENT.md) for exact static paths.

The preserved `article-01.1` evidence predates this standalone repository;
its Git metadata identifies the original staging checkout. `article-01.2` is
the publication-preparation rerun from the standalone source commit. Each
manifest records the exact source files and environment used for its run.
Frozen publication-link fields describe that evidence release; they do not
describe the current availability of the repository or companion article.

Code and original documentation retain the [MIT license](LICENSE) from the
source project. Referenced papers and external projects retain their own terms.

## Files and responsibility

| Path | Responsibility |
| --- | --- |
| `lab/memory.py` | Writer, version history, immutable gates, retrieval, fixed consumer |
| `lab/runner.py` | Candidate validation, isolated evaluations, metrics, evidence export |
| `lab/__main__.py` | CLI, trace diagnosis, proposal packets, explicit review records |
| `data/scenarios.json` | Original public normalized events and expected answers |
| `experiments/` | Baseline, candidate lineage, mutation and budget contract |
| `tests/test_lab.py` | Runnable regression and invariant checks |
| `artifacts/article-01.2/` | Frozen measured evidence used by the draft and explorer |
| `web/` | Small static presentation; no second implementation of the evaluator |
| `docs/` | Research and the public artifact contract |

## What these results do not establish

- **No blind held-out claim.** Search, evaluation, and adversarial roles are
  public diagnostic/regression groups. All were visible while the candidates
  were authored. A later generalization experiment needs fresh inaccessible
  tasks and a frozen candidate before evaluation.
- **No stochastic confidence claim.** Three repeats check reproducibility and
  sample local timing. They produce the same answers; zero score variance does
  not increase the number of independent tasks.
- **No production benchmark.** Exact matching on original synthetic scenarios
  does not measure real-world assistant quality. Context words are whitespace
  counts; model tokens and provider expenditure are zero. CPU timing excludes
  artifact export, authoring effort, hardware cost, and real model latency.
- **No hostile-code sandbox.** Validated configuration files cannot replace the
  evaluator, but a coding agent with the same filesystem permissions can edit
  source. Run an untrusted proposer in a separate restricted environment before
  granting it autonomy. The demo only executes its own trusted Python.
- **No general poisoning/secret detector.** The target's durable key, source and
  kind allowlist covers explicit structured cases. It does not classify arbitrary
  text or protect against secrets disguised as an allowed city or language.

The next article should challenge the evaluator and the evidence boundary
before adding a stronger proposer or more experiments.
