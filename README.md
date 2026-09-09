# Closed-Loop AI Lab

Why does a memory system answer **Paris** when the user still lives in **Berlin**?
This small Python experiment reproduces that mistake, changes the memory rules,
and checks whether the fix helps across 20 scenarios. A browser page lets you
compare the saved answers and inspect how each answer was produced.

This is one example of **closed-loop AI engineering**: observe a failure → propose
a limited change → evaluate it against the previous version → review the evidence
before accepting the change. Here the change is a memory configuration. The
experiment uses ordinary Python rules throughout, so you can follow every step
without an LLM, API key, or paid service.

[Source on GitHub](https://github.com/slavadubrov/closed-loop-ai-lab) ·
[Run locally](#run-it) · [Deployment guide](DEPLOYMENT.md).
The companion article is awaiting publication; this walkthrough stands on its own.

## Start with the city example

Imagine an assistant remembering Ada's account details. These sentences explain
the test inputs; the program actually receives JSON, shown below.

| Event      | What Ada reports or asks         | What should happen                                                 |
| ---------- | -------------------------------- | ------------------------------------------------------------------ |
| January 1  | “My city is Berlin.”             | Store Berlin, effective January 1.                                 |
| January 3  | “I move to Paris on January 10.” | Store the future change without making Paris the current city yet. |
| January 5  | “What is my city today?”         | Answer **Berlin**.                                                 |
| January 12 | “What is my city today?”         | Answer **Paris**.                                                  |

After both writes, the program has these two records:

| Subject       | Property | Value  | Recorded on | Valid from | Valid until          |
| ------------- | -------- | ------ | ----------- | ---------- | -------------------- |
| Ada's account | city     | Berlin | January 1   | January 1  | January 10, excluded |
| Ada's account | city     | Paris  | January 3   | January 10 | No end date          |

The **baseline** stores this history, but does not check the validity date when
retrieving it. Both city records match the query, and the more recently recorded
Paris comes first. The answer function takes the first matching city record.
It therefore answers `["Paris", "Paris"]` to the two questions.

The **Scoped history** candidate filters records by the requested subject and
date before ranking them. On January 5 only Berlin is valid; on January 12 only
Paris is valid. It answers `["Berlin", "Paris"]`. The stored facts did not change;
the rule for selecting them did.

### What exactly goes into the program?

The input file is [data/scenarios.json](data/scenarios.json). Each scenario is a
sequence of `write`, `query`, and sometimes `delete` events. The Python runner
feeds those events into the memory program, called the **target** in the reports.
There is no chat-to-JSON extraction step in this demo.

This is the complete January 3 write event from `future-move`:

```json
{
  "action": "write",
  "at": "2026-01-03",
  "tenant": "north",
  "user": "ada",
  "should_retain": true,
  "fact": {
    "tenant": "north",
    "user": "ada",
    "entity": "account",
    "key": "city",
    "value": "Paris",
    "confidence": 0.95,
    "valid_from": "2026-01-10",
    "source": "user",
    "kind": "fact"
  }
}
```

Read `fact` as a request to save **Ada's account city = Paris, effective January
10**. It is a proposal because the writer can reject it before storing it.

| Field              | Meaning in this event                                                                                                                      |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `tenant`, `user`   | The owner: Ada in the fictional `north` workspace. The writer checks that the fact's owner matches the request's owner.                    |
| `entity`           | Which subject the property belongs to: `account`. Other scenarios distinguish `home` from `work`.                                          |
| `key`, `value`     | The property `city` and its proposed value `Paris`.                                                                                        |
| `at`, `valid_from` | Received January 3; becomes true January 10. These dates serve different purposes.                                                         |
| `confidence`       | A hand-authored input score. The baseline admits scores of at least `0.7`; this score is `0.95`. It is not a calibrated model probability. |
| `source`, `kind`   | Labels checked by the writer's fixed admission rules: a user-supplied fact.                                                                |
| `should_retain`    | The evaluator's label: this is a useful proposal that should be kept. The target ignores this field.                                       |

**Confidence decides whether to store a proposed fact.** The writer rejects
a proposal when its supplied score is below `min_confidence`. For example,
`delivery = courier` scored `0.4` is rejected at the baseline threshold of
`0.7`, but stored at Broad writes' threshold of `0.2`. The program does not
calculate this score or turn it into a probability of correctness.

The January 5 query is another event:

```json
{
  "action": "query",
  "at": "2026-01-05",
  "tenant": "north",
  "user": "ada",
  "entity": "account",
  "key": "city",
  "as_of": "2026-01-05",
  "text": "city",
  "expected": "Berlin"
}
```

This asks for Ada's account city **as of January 5**. The target retrieves records,
packs them within a small word budget, and returns the first packed record with
`key: "city"`. If none matches, it returns `null`, meaning no answer.
The evaluator then compares the returned value with `expected`.

The fixture includes `expected` and `should_retain` for scoring. The fixed target
ignores both fields, although the runner passes the complete event into it.
These public fixtures are not a hidden test set.

## What is a scenario and an event?

A **scenario** is one complete test story. The future-move story above has four
**events**: save Berlin, save Paris, ask for January 5, and ask for January 12.
An event is one action sent to memory: `write`, `query`, or `delete`.

The repository supplies **20 scenarios**. Each configuration runs through the
same stories once, starting with empty memory for each story.

Thus **4 configurations × 20 scenarios = 80 scenario-runs**.
There are still only 20 different stories. No model is called to generate inputs,
choose settings, answer questions, or score these runs.

## What are the four candidates?

A candidate is a **configuration of the same memory program**, not a different
model or agent. Its **parent** is the configuration it starts from. Each candidate
receives the same events, with fresh memory at the start of each scenario.

| Browser label / configuration ID           | Starts from           | What changes, with an example                                                                                                                                | Scenarios passing |
| ------------------------------------------ | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------: |
| Baseline / `baseline`                      | Initial configuration | Accept confidence ≥ `0.7`; retrieve matching records without filtering their subject or validity date. This returns Paris too early.                         |             13/20 |
| Scoped history / `scoped-history`          | Baseline              | Enable subject and date filters. Select Berlin for January 5, and avoid answering a question about `home` with the city stored for `work`.                   |             19/20 |
| Deduplicate confirmations / `deduplicated` | Scoped history        | Keep one active record when the same fact is confirmed again. Three confirmations of `language = German` use one row instead of three, with the same answer. |             19/20 |
| Write more / `broad-writes`                | Scoped history        | Lower the admission threshold from `0.7` to `0.2`. A speculative `delivery = courier` scored `0.4` can replace confirmed `pickup`, making the answer wrong.  |             16/20 |

The last two are separate branches from Scoped history. Write more does **not**
inherit deduplication. Scoped history changes two filters together, so its score
measures that combined change.

Why include a worse candidate? Write more retains all 38 useful proposals per
pass through the suite, compared with its parent's 37, but also admits four unnecessary ones.
It fixes one scenario and breaks four: success falls from 19/20 to 16/20.
**Keeping more useful facts does not necessarily produce better answers.**

Codex authored the original candidates during development with access to all
scenarios. Running this repository replays those configurations; it does not
ask a model to invent new ones.

### Two JSON files with different jobs

[experiments/candidates.json](experiments/candidates.json) lists the **four
configurations to test**. For example, `scoped-history` starts from `baseline`
and changes two settings in its `patch`:

```json
{
  "filter_entity": true,
  "time_aware": true
}
```

These switches enable subject and date filtering. The record's other fields
name the configuration, identify its parent, explain why the change might help,
and record who proposed it. Only the settings in `patch` change the memory rules.

[experiments/contract.json](experiments/contract.json) lists **what changes and
run sizes are allowed**. Its larger numbers are maximum limits:

| Item | Supplied experiment | Maximum allowed |
| --- | --- | --- |
| Configurations, counting the baseline | 4 | 8 |
| Scenarios per configuration | 20 | 64 |
| Events per scenario | Varies; `future-move` has 4 | 64 |
| Repeats per scenario | 3 | 5 |

There are no four hidden candidates. The limit of eight leaves room to evaluate
additional configurations, including their earlier parents. The runner also
limits evaluation time to 30 seconds. A "campaign" in the code means the whole
batch of configuration tests.

A candidate may change only `min_confidence`, `filter_entity`, `time_aware`,
`deduplicate`, and `top_k`. It cannot turn off user isolation, change expected
answers, or replace the Python implementation through this JSON file. The same
tests and required data rules apply to every configuration.

## What are we measuring?

The main outcome is **scenario success**: every answer must equal its expected
answer, and every performed hard-constraint check must pass. The city scenario
has two questions but counts as one scenario. `19/20` means 19 complete scenarios
passed.

The report also explains _why_ the result changed:

| Measure                         | Question it answers                                                                                                   |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Useful-write precision / recall | Of the proposals kept, how many were labelled useful? Of all useful proposals, how many were kept?                    |
| Relevant-memory recall          | Did retrieval include the needed fact? Finding Berlin somewhere in the list is weaker than actually answering Berlin. |
| Distracting-memory rate         | How many retrieved records were irrelevant to the expected answer, subject, or date?                                  |
| Stored records / bytes          | How much memory remained at the end of each scenario? Deduplication can reduce this without improving answers.        |
| Context words                   | How many whitespace-separated words were packed for the answer function? This is not a model-token count.             |
| Local p50 / p95 time            | Median and slower-end Python scenario durations, including tracing and scoring work. No model latency is measured.    |

A **violation** is a failed hard-constraint check. These rules are fixed across
all candidates:

| Check             | Concrete example                                                                                                      | Recorded failures / checks per candidate |
| ----------------- | --------------------------------------------------------------------------------------------------------------------- | ---------------------------------------: |
| Owner isolation   | Ada's query must not retrieve another user's records; a write claiming a different owner must leave memory unchanged. |                                   0 / 28 |
| Deletion          | Deleting Ada's `account/city` removes every version in that scope; those deleted record IDs must not reappear later.  |                                   0 / 11 |
| Prohibited writes | A proposal with a disallowed key, source, or kind must be rejected without changing memory.                           |                                    0 / 2 |

These counts cover individual events in one run of the 20 scenarios. Deletion checks concern the target's memory; saved traces
still contain earlier states. The structured admission rules are not a general
secret or prompt-injection detector.

The frozen experiment contains **20 scenarios × 4 configurations =
80 scenario-runs**. Each story runs once per configuration. All four configurations pass the implemented hard checks, so their answer
quality still needs a separate comparison.

The evaluator recommends accept or reject based on the results. Every human
review is still pending. A recommendation neither approves nor deploys a change.
See the [readable comparison report](artifacts/article-01.3/report.md) and
[exact counts in bundle.json](artifacts/article-01.3/bundle.json) under each
candidate’s `summary.counts`.

## Run it

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run:

```sh
git clone https://github.com/slavadubrov/closed-loop-ai-lab.git
cd closed-loop-ai-lab
uv run --frozen python -m lab run
```

The command runs the baseline plus three candidates, each on 20 independent
synthetic scenarios once. It creates a new `artifacts/local-<timestamp>/`
directory containing a complete report, metrics, traces, state diffs, input
snapshots, and a SHA-256 manifest. It never overwrites another run.

Python 3.12+ is required; uv can provision the interpreter. The first setup
downloads the pinned Ruff development tool. After setup, the experiment itself
uses only the standard library and performs no network calls. To omit developer
tools, use `uv run --frozen --no-dev python -m lab run`.

Open the **saved experiment** in the browser:

```sh
uv run --frozen python -m lab serve
```

Visit [http://127.0.0.1:8000/web/](http://127.0.0.1:8000/web/). It serves on
loopback only. The explorer initially uses `artifacts/article-01.3/`, the evidence explained above. Fresh runs keep their own directories; open
their `report.html` through the same server to inspect their results. Stop the
server with Ctrl+C.

### What to do on the page

1. Read the city example at the top. The explorer opens **Scoped history** on
   **future-move**, the same example.
2. Compare the original answers `["Paris", "Paris"]` with the selected answers
   `["Berlin", "Paris"]`. They correspond to January 5 and January 12.
3. Use **Show full trace** and **Inspect stored state & retrieval** to see the
   inputs, selected records, and answer for each event.
4. Choose **Write more**, the **Conflict** group, and **Do not promote an uncertain
   contradiction** to inspect the `pickup` → `courier` regression. The full metric
   table compares this candidate with its parent, Scoped history.

The selectors only switch between **saved results**. They do not edit memory,
run Python, or call a model. To produce a new experiment, use `lab run` or the
candidate workflow below. The browser is plain HTML, CSS, and JavaScript, with
no frontend build step or runtime application server.

## Run the improvement loop

To try an additional configuration, first export the baseline settings and its
failed tests from the `search` group. This group supplies the examples a proposer
can inspect; all three groups (`search`, `evaluation`, `adversarial`) are public:

```sh
uv run --frozen python -m lab packet \
  --release artifacts/article-01.3 --output proposal-packet.json
```

The packet is a JSON file containing the baseline settings, allowed changes,
source-file hashes, and the inputs and answers from failed tests. The command
only exports data; it does not contact an AI provider. You can give the file to a
coding assistant and ask for a new configuration record in the format shown in
`experiments/candidates.json`, including an accurate record of who proposed it.

For a fully local demonstration, two deterministic diagnosis rules inspect the
wrong-answer record: wrong entity enables entity filtering; invalid date enables
temporal filtering. They generate a new candidate from the actual trace:

```sh
uv run --frozen python -m lab propose \
  --release artifacts/article-01.3 --output diagnosed-candidate.json
uv run --frozen python -m lab evaluate \
  --release artifacts/article-01.3 --candidate diagnosed-candidate.json
```

These commands add a fifth configuration, `diagnosed-history`, to the original
four. The new batch runs 5 × 20 = 100 scenario-runs. For the supplied
failures, the helper enables the same filters as Scoped history; it demonstrates
how a proposed change reaches evaluation, not a newly discovered strategy.

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
The whole batch may contain at most eight configurations, counting the baseline
and earlier configurations as well as new proposals. Output files
are created exclusively; choose a new path to repeat an export.

The settings a candidate may change are `min_confidence`, `filter_entity`,
`time_aware`, `deduplicate`, and `top_k`. Their types and ranges are checked
before execution. Unknown fields, non-finite thresholds, out-of-budget runs,
and attempts to disable owner isolation, deletion, or prohibited-write rules
are rejected. `experiments/contract.json` documents the boundary. Each scenario
starts with new in-memory state; no candidate source code is loaded or executed.

When **you** have reviewed a candidate, this optional command records your
decision separately from the frozen evidence:

```sh
uv run --frozen python -m lab decision \
  --release artifacts/article-01.3 --candidate scoped-history \
  --verdict accept --reviewer "Your name" --reason "Your evidence-based rationale"
```

Use `--verdict reject` for rejection. These are explicit operator declarations,
not independently authenticated identities. The command only appends a review
record under `decisions/`; it never deploys, changes the running target, or
rewrites the original bundle. The browser displays the saved recommendation and pending review status; it
does not record a decision.

## Verify it

```sh
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen ruff check lab tests
uv run --frozen ruff format --check lab tests
uv run --frozen python -m lab verify artifacts/article-01.3 --source
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
its Git metadata identifies the original staging checkout. `article-01.2`
preserves the earlier three-run experiment. The current `article-01.3` evidence
runs each story once per configuration. Each
manifest records the exact source files and environment used for its run.
Frozen publication-link fields describe that evidence release; they do not
describe the current availability of the repository or companion article.

Code and original documentation retain the [MIT license](LICENSE) from the
source project. Referenced papers and external projects retain their own terms.

## Files and responsibility

| Path                      | Responsibility                                                       |
| ------------------------- | -------------------------------------------------------------------- |
| `lab/memory.py`           | Writer, version history, immutable gates, retrieval, fixed consumer  |
| `lab/runner.py`           | Candidate validation, isolated evaluations, metrics, evidence export |
| `lab/__main__.py`         | CLI, trace diagnosis, proposal packets, explicit review records      |
| `data/scenarios.json`     | Original public normalized events and expected answers               |
| `experiments/`            | Baseline, candidate lineage, mutation and budget contract            |
| `tests/test_lab.py`       | Runnable regression and invariant checks                             |
| `artifacts/article-01.3/` | Frozen measured evidence used by the draft and explorer              |
| `web/`                    | Small static presentation; no second implementation of the evaluator |
| `docs/`                   | Research and the public artifact contract                            |

## What these results do not establish

- **No blind held-out claim.** Search, evaluation, and adversarial roles are
  public diagnostic/regression groups. All were visible while the candidates
  were authored. A later generalization experiment needs fresh inaccessible
  tasks and a frozen candidate before evaluation.
- **Deterministic results.** The default is one run per story. Repeating the
  same inputs adds no answer-quality evidence. `--repeats N` remains available
  for explicit reruns, but does not add an LLM or simulate model variability.
  A future model-backed evaluation would need repeated trials if outputs vary,
  with the model and generation settings recorded.
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
