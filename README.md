# Meta-Engineering AI Lab

Companion code for **Meta-Engineering AI Systems**, a series about closed-loop AI engineering: an agent proposes changes, experiments test them, and feedback guides the next attempt. Every part uses the same small, deterministic memory tool.

| | Part 1: from traces to better memory | Part 2: make it scorable before you make it autonomous |
| --- | --- | --- |
| Article | [Published 2026-09-12](https://slavadubrov.com/blog/2026/09/12/from-traces-to-better-memory/) | Not yet published |
| What it shows | An LLM agent reads failures and improves the memory tool's settings, from 13/20 to 20/20 scenarios. | A configuration with 8/8 correct answers also stores four unwanted facts; state, audit and previous-suite checks catch it. |
| Run it | `python -m lab campaign --live` (needs `OPENAI_API_KEY`) | `python -m lab.evaluator_exploits` (no key) |
| Browser page | `web/index.html`, `web/memory.html` | `web/evaluators.html` |
| Report | [reports/agent-study-03.md](reports/agent-study-03.md) | [reports/article-02/grid/report.md](reports/article-02/grid/report.md), [Jev report](reports/article-02/jev/report.md) |
| Code at publication | tag `v0.2.2` | this branch |

## Quick start (no key needed)

```sh
git clone https://github.com/slavadubrov/meta-engineering-ai-lab.git
cd meta-engineering-ai-lab
uv sync --frozen
uv run --frozen python -m lab.evaluator_exploits --output artifacts/my-evaluator-study
```

Expected output:

```text
Executed 1600 fresh-state scenario runs; zero model calls.
Answer-only winner: threshold-0.2-k1.
Decision with every check: keep the incumbent threshold-0.6-k3.
```

To open the browser pages, download the Part 1 evidence once (4.1 MB, checked against a pinned SHA-256; it makes no model calls), then start the local server:

```sh
uv run --frozen python scripts/fetch_evidence.py
uv run --frozen python -m lab serve --port 8075
```

Open http://127.0.0.1:8075/web/evaluators.html for Part 2 and http://127.0.0.1:8075/web/ for Part 1. The server listens on loopback only and serves only `web/`, `artifacts/`, `reports/` and `experiments/`. Stop it with Ctrl-C. The Part 2 page works without the Part 1 download.

## Part 1: from traces to better memory

An **outer LLM agent improves a memory tool**. It reads recorded failures, proposes a small configuration change, receives the Python evaluation, and chooses what to try next. The memory tool is deterministic; the agent choosing its changes uses GPT-5.6 Luna.

Start with the failure: Ada lives in Berlin and reports a move to Paris effective next week. The memory tool returns Paris when asked where she lives today. The agent studies that trace and can change the rules for storing and retrieving facts.

```text
Run the original memory tool → give its failures to the agent
                                      ↓
                    SGR observations, hypothesis, patch
                                      ↓
                    Python validates and tests the patch
                                      ↓
                    Return results or rejection to the agent
                                      ↓
                    Next proposal, until stop or limit
```

The recorded study contains **actual saved OpenAI requests and responses**. Compact reports and selected examples are in `reports/`; complete recordings are in a [release archive](reports/evidence.json) restored by `scripts/fetch_evidence.py`. The browser shows that evidence without making API calls. The [memory-tool walkthrough](docs/memory-tool.md) explains the deterministic component in detail.

To reproduce the article exactly, use its tag. No key needed:

```sh
git clone --branch v0.2.2 --depth 1 https://github.com/slavadubrov/meta-engineering-ai-lab.git
cd meta-engineering-ai-lab
uv sync --frozen
uv run --frozen python scripts/fetch_evidence.py
uv run --frozen python -m lab verify artifacts/agent-study-03 --source
```

Expected output: `Verified 1367 artifact hashes and current source`. On later code, drop `--source`: the evidence hashes still verify, and a test checks that the current code reproduces every recorded Part 1 score.

In the browser, choose campaign 1, then follow its four iterations. Each shows the input, model proposal, validation or evaluation result, and whether that change became the next experimental parent. For the city records and four teaching configurations, open **Part 1: memory tool** (`/web/memory.html`).

The archive also keeps earlier development runs (`agent-pilot-01`, `agent-study-01`, `agent-study-02`, `article-01.1` to `article-01.5`). They are evidence of their own runs; the article uses `agent-study-03` and `article-01.6`.

### What happened in the recorded study?

Each of three campaigns started with the same baseline and fresh agent history. The first request contained only baseline evidence; it did not include the three hand-prepared improved configurations used in the separate memory walkthrough.

| Campaign | Model calls | Proposals tested | Invalid proposals | Starting success | Selected success |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 4 | 3 | 0 | 13/20 | 20/20 |
| 2 | 4 | 3 | 0 | 13/20 | 20/20 |
| 3 | 4 | 3 | 0 | 13/20 | 20/20 |

In campaign 1:

1. The agent enabled subject and date filtering. Python measured an improvement from 13/20 to 19/20 passing scenarios.
2. The agent proposed deduplication. Answers stayed at 19/20 while mean stored records fell from 1.70 to 1.60.
3. The agent lowered the storage-confidence threshold from 0.7 to 0.6. The remaining useful preference was retained, bringing success to 20/20 and mean storage to 1.65 records.
4. The agent returned a stop decision because it had no further supported change to propose from the supplied evidence.

All three agents chose to stop within the four-decision limit. They chose the same sequence and final settings in this study. A stop decision is not proof of a globally optimal configuration.

The estimated cost of the 12 model calls was **$0.039177**, against a **$0.50** budget. This estimate uses recorded usage and the published Luna rates checked on September 11, 2026. It includes cache-write surcharges and ignores cache-read discounts; it is not an invoice. Local CPU, hardware, and development costs are separate.

**20/20 is a result on these public development stories.** It does not establish production quality, unseen-task performance, or an advantage over human or classical search.

### What is a campaign, an iteration, or a scenario?

- A **campaign** is one complete attempt to improve the baseline, with fresh agent history.
- An **iteration** is one model decision: propose a change or stop. A proposal can be rejected before evaluation.
- A **candidate** is a configuration of the same Python memory tool. Its **parent** is the configuration it changes.
- A **scenario** is a complete test story. It starts with empty memory and contains events: `write`, `query`, or `delete`.
- An **event** is one action. The future-move story writes Berlin, writes future Paris, asks for January 5, and asks for January 12.

A new configuration runs the 20 scenarios **once**. The runner reuses verified deterministic parent evidence for comparisons. Repeating the same memory test would add no answer-quality evidence. We repeat the agent's entire campaign because its decisions can vary.

### Where is the LLM, and where is it absent?

| Component | What executes |
| --- | --- |
| Outer proposer | The LLM receives traces and feedback, then returns an SGR decision record. |
| Proposal validation | Python checks structure, permitted settings, event references, and duplicate configurations. |
| Memory tool | Ordinary Python stores prepared facts and selects values from records. |
| Evaluator | Python checks expected answers, state, owner isolation, deletion, and prohibited writes. |
| Browser | JavaScript displays saved evidence. No API key or provider call. |

The memory tool does not extract facts from conversation or generate natural-language answers. The test supplies `city = Paris`, its date, owner, and other fields as JSON. The writer validates those fields, creates a versioned record in an in-memory list, and retrieves a value. See [the concrete input and storage walkthrough](docs/memory-tool.md#what-exactly-goes-into-the-program).

**Confidence decides whether a proposed fact is stored.** It is a supplied test score, not a model-calibrated probability. The writer rejects scores below `min_confidence`. A `delivery = courier` proposal scored `0.4` is rejected at threshold `0.7` and stored at `0.2`. The agent's successful `0.6` threshold admits a useful preference scored `0.6` while keeping the uncertain `0.4` proposal out.

### Where SGR and SGAM apply

**Schema-Guided Reasoning (SGR) governs every LLM response:** observations, hypothesis, expected effect,
action, and a bounded patch. **Schema-Guided Agent Memory (SGAM) governs the stored facts:** a typed record
with a schema version, owner, source event, and validity dates. Python enforces
these rules before changing memory; a schema-valid proposal alone cannot bypass
them.

For example, Paris becomes valid on January 10 and links to the Berlin record
it replaces. A conflicting `city = Rome` for that same effective date is rejected
without changing either record. Repeating Paris for that same date reuses it.
Deletion removes all versions for the requested owner, subject, and property.
The [memory walkthrough](docs/memory-tool.md#how-the-memory-schema-governs-a-write)
shows the complete stored JSON and conflict rules.

This demonstrates selected SGAM lifecycle rules in memory. It has no database,
retention service, or migration engine. The baseline's missing subject/date
filters are deliberate faults for the agent to repair, while ownership, schema
validation, and conflict handling apply to every configuration.

### What the agent is allowed to change

| Setting | Allowed values | Meaning |
| --- | --- | --- |
| `min_confidence` | 0–1 | Minimum supplied score for storing a fact. |
| `filter_entity` | Boolean | Restrict retrieval to the requested subject. |
| `time_aware` | Boolean | Restrict retrieval to the requested validity date. |
| `deduplicate` | Boolean | Reuse an identical active fact. |
| `top_k` | Integer 1–8 | Maximum retrieved records before packing context. |

Each proposal changes at most **two** settings. The model cannot edit source, test inputs, expected answers, scoring, data-isolation rules, budgets, or release authority. It has no filesystem, shell, browsing, or other tools. The runner, not the model, assigns candidate IDs and the current parent.

Every API call requests strict Structured Outputs through the Pydantic-generated [SGR schema](lab/agent.py):

```text
observations[] → hypothesis → predicted_effect → action → patch
```

Observations cite a supplied scenario and event number. `action` is `propose` or `stop`; every patch field is present, with `null` for unchanged settings. Python rejects nonexistent references, unsupported values, empty/no-op proposals, and previously tested configurations. A stop decision must have an empty effective patch.

The schema constrains the response shape. It does not prove the model's explanation correct. The final study had no invalid proposals. A separate preserved development study demonstrates that distinction: three schema-valid responses had invalid evidence references and were rejected. The current controller returns both the rejected output and a specific validation error to the next call; offline tests verify that feedback path.

### Run a new live campaign

Needs `OPENAI_API_KEY`. Copy `.env.example` to `.env.local` (ignored by Git) and fill in the key with an editor. Do not put the key in the browser or publish it with a static site.

```sh
uv run --frozen --env-file .env.local python -m lab campaign \
  --live --campaigns 3 --iterations 4 --budget-usd 0.50 \
  --output artifacts/my-agent-study
```

`--live` is required for provider execution. An environment key never silently turns an offline command into live execution. Defaults are three campaigns, four decisions each, and a USD 0.50 budget. Hard limits are five campaigns, four decisions per campaign, and USD 2.

Each call uses Luna with reasoning effort `low`, at most 4,096 output tokens, a 60-second timeout, and no automatic SDK retries. The runner reserves a conservative request cost before calling. An unknown-cost failure keeps that reservation and stops the affected campaign. The transcript records errors rather than substituting a scripted proposal.

Read `artifacts/my-agent-study/report.md`. To view your results in the browser, export a new static folder:

```sh
uv run --frozen python -m lab site \
  --campaign-release artifacts/my-agent-study --output my-study-site
python -m http.server 8076 --bind 127.0.0.1 --directory my-study-site
```

Open `http://127.0.0.1:8076/`. Stop the server with Ctrl-C. Output directories are created exclusively; choose a new name for another run or export.

### What is saved, and what does “selected” mean?

Generated evidence stays outside Git. Each iteration saves the exact request (including instructions and schema), provider response, usage, timing, validation result, and completed Python evaluation. Evaluation folders contain traces, state changes, metrics, and file hashes. The root manifest covers every saved file and identifies the source used for the study.

A new parent must pass every hard check and either improve complete-scenario success or preserve that score while using fewer stored records. A rejected change leaves the previous parent intact. The next request receives the proposal's outcome either way.

**Selected means selected for continued experimentation.** It does not authorize a production release. Human adoption review remains separate; nothing is deployed.

The 20 stories are public development cases. The original `search`, `evaluation`, and `adversarial` labels organize them but provide no hidden holdout. A coding agent with independent filesystem access would need a separate sandbox; this model is restricted by the capabilities actually provided to its API call.

## Part 2: make it scorable before you make it autonomous

Part 2 asks whether the score an improvement loop optimizes supports the decision to keep a change. It reuses the Part 1 memory tool, runner and verifier.

```text
8 configurations (threshold 0.2 / 0.4 / 0.6 / 0.7 × top_k 1 / 3)
        ↓
Answers only on 8 development cases ─→ picks threshold-0.2-k1 (8/8, stores 4 unwanted facts)
        ↓ + state checks: no write labeled should_retain=false may change memory
threshold-0.4-k1 (8/8, no unwanted development writes)
        ↓ + 12 audit cases hidden from the selector
threshold-0.6-k1 (12/12)
        ↓ + 20 Part 1 scenarios, hard constraints, context and latency budgets
threshold-0.6-k1 and threshold-0.6-k3 (the incumbent) pass every check
        ↓ adoption rule: replace the incumbent only with ≥1 paired win and no losses
keep the incumbent threshold-0.6-k3 (threshold-0.6-k1 ties it on all 40 scenarios)
```

No LLM runs in this experiment and no key is needed. All five fresh-state sweeps give identical results; the runner stops if one does not. The audit cases are hidden from the selector, not from the author, so they are not a blind test. The 12 audit cases come from 2 templates and the 8 development cases from 3, so the report counts wins and losses per template. Read [the full result table](reports/article-02/grid/report.md).

The committed evidence in `reports/article-02/grid/` has a `manifest.json`; check it with `uv run --frozen python -m lab verify reports/article-02/grid`. A fresh run writes the same `report.md`; only timings in `bundle.json` and `runs.jsonl.gz` differ.

### Compare Jev with exact matching

[Jev 1.13](https://openrouter.ai/typesafe/jev-1.13) returns typed decisions instead of chat text. `lab/jev_compare.py` calls OpenRouter's alpha [Decisions API](https://github.com/OpenRouterTeam/typescript-sdk/blob/main/src/funcs/alphaDecisionsCreate.ts) at `https://openrouter.ai/api/alpha/decisions`. Ten authored cases in `experiments/evaluator-exploits/judge-cases.json` separate a correct answer from acceptable behavior. Case IDs (`c01`…`c10`) carry no label, and the labels and hard failures are not sent.

The [committed live run](reports/article-02/jev/report.md) (2026-09-23, model snapshot `typesafe/jev-1.13-20260917`, billed $0.000172 for two calls):

| Method | Scored against | Agreement |
| --- | --- | ---: |
| Exact match | answer labels | 8/10 |
| Exact match + hard checks | behavior labels | 8/10 |
| Jev, answer only | answer labels | 10/10 |
| Jev + hard checks | behavior labels | 10/10 |
| Jev, given state evidence | behavior labels | 10/10 |

Exact matching rejects the two valid paraphrases. Jev accepts them. Python rejects the three cases with recorded hard failures whatever Jev says: `eligible = jev_accepts and not hard_failures`. The state-aware arm gets more evidence and a stronger rubric, so it cannot show better reasoning on its own. These are ten public examples, not an error rate or a human calibration.

Offline, no key needed. This records the exact-match baselines and marks Jev as not run:

```sh
uv run --frozen python -m lab.jev_compare --output artifacts/jev-offline
uv run --frozen python -m lab verify artifacts/jev-offline
```

Live, needs `OPENROUTER_API_KEY` in `.env.local` (copy `.env.example`). It makes two requests, each at most 24 KB, with a 60-second socket timeout and no retries:

```sh
uv run --frozen --env-file .env.local python -m lab.jev_compare --live --output artifacts/jev-live
uv run --frozen python -m lab verify artifacts/jev-live
```

The request limits are not a spending cap; set a limit on the OpenRouter key for that. Returned usage and billed cost are recorded; a missing cost stays unknown. Provider IDs, headers and error text are not saved. In the Part 2 page you can load your own `study.json`; the file is read locally.

### Where each article section lives

| Article section | Files |
| --- | --- |
| A correct answer can hide the wrong memory | `experiments/evaluator-exploits/scenarios.json` (`dev-01`), `state_violations` in `lab/evaluator_exploits.py` |
| Reproduce the false winner | `experiments/evaluator-exploits/contract.json`, `lab/evaluator_exploits.py`, `reports/article-02/grid/report.md` |
| A holdout is defined by how its feedback is used | `selection.json` in the grid evidence (development scores only, `audit_access: false`) |
| Count independent evidence, not executions | `summarize` and `compare` in `lab/evaluator_exploits.py`; the paired table in the report |
| Add a semantic judge | `lab/jev_compare.py`, `experiments/evaluator-exploits/judge-cases.json`, `reports/article-02/jev/` |
| Make adoption an explicit decision | `adoption_rule` in the contract; `adoption` and `decision` in `lab/evaluator_exploits.py` |
| Run and inspect the companion | `web/evaluators.html`, `web/evaluators.js` |

## Verify and navigate the code

No key needed:

```sh
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen python -m unittest discover -s scripts -v
uv run --frozen ruff check lab tests scripts
uv run --frozen ruff format --check lab tests scripts
uv run --frozen python -m lab verify artifacts/agent-study-03
uv run --frozen python -m lab verify reports/article-02/grid
uv run --frozen python -m lab verify reports/article-02/jev
```

Tests use scripted transport to check the real controllers without provider calls. They also check that the current code reproduces the recorded Part 1 scores and that a fresh Part 2 run matches the committed report. CI runs these commands, the documented quick start, and a browser smoke test (`web/smoke.mjs`) of all three pages.

| File | Responsibility |
| --- | --- |
| [lab/memory.py](lab/memory.py) | The deterministic tool: writes, validity history, retrieval, and deletion. |
| [lab/runner.py](lab/runner.py) | Scenario runs, scoring, evidence export, and verification. |
| [lab/agent.py](lab/agent.py) | Part 1: SGR models, instructions, permissions, API request, and token-cost accounting. |
| [lab/campaign.py](lab/campaign.py) | Part 1: fresh campaigns, feedback, selection, budgets, and the campaign report. |
| [lab/evaluator_exploits.py](lab/evaluator_exploits.py) | Part 2: the eight-candidate grid, evidence layers, adoption rule, and report. |
| [lab/jev_compare.py](lab/jev_compare.py) | Part 2: exact matching and Jev on ten authored cases. |
| [lab/\_\_main\_\_.py](lab/__main__.py) | CLI commands, the local server, and the static site export. |
| [web/](web/) | Three static pages that display saved evidence. No API key or provider call. |

## Host the pages as a static site

```sh
uv run --frozen python -m lab site --output site
python -m http.server 8076 --bind 127.0.0.1 --directory site
```

`lab site` needs the Part 1 evidence download. It copies the three pages, the verified Part 1 evidence and the committed Part 2 evidence into `site/`, with relative links, so the folder works under any URL prefix. It refuses to overwrite an existing folder. Pass `--campaign-release artifacts/my-agent-study` to show your own campaign.
