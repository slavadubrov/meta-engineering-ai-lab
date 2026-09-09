# Closed-Loop AI Lab

An **outer LLM agent improves a memory tool**. It reads recorded failures, proposes a small configuration change, receives the Python evaluation, and chooses what to try next. The memory tool is deterministic; the agent choosing its changes uses GPT-5.6 Luna.

Start with the failure: Ada lives in Berlin and reports a move to Paris effective next week. The memory tool returns Paris when asked where she lives today. The agent studies that trace and can change the rules for storing and retrieving facts.

```text
Run the original memory tool → give its failures to Luna
                                      ↓
                    SGR observations, hypothesis, patch
                                      ↓
                    Python validates and tests the patch
                                      ↓
                    Return results or rejection to Luna
                                      ↓
                    Next proposal, until stop or limit
```

The repository includes **actual saved OpenAI requests and responses**, not a simulated agent transcript. The browser shows that evidence without making API calls. A separate memory walkthrough explains the deterministic component in detail.

[Recorded study](artifacts/agent-study-02/report.md) · [Memory-tool walkthrough](docs/memory-tool.md) · [Deployment](DEPLOYMENT.md)

The companion article is awaiting publication. This README and the browser guide stand on their own.

## Inspect the saved campaigns without a key

```sh
git clone https://github.com/slavadubrov/closed-loop-ai-lab.git
cd closed-loop-ai-lab
uv sync --frozen
uv run --frozen python -m lab verify artifacts/agent-study-02 --source
uv run --frozen python -m lab serve --port 8075
```

Open **http://127.0.0.1:8075/web/**. Choose campaign 1, then follow its four iterations. Each shows the input, model proposal, validation or evaluation result, and whether that change became the next experimental parent. Stop the server with Ctrl-C.

For the city records and four teaching configurations, open **Understand the memory tool**, or `/web/memory.html`. Its controls explore saved Python results rather than calling a model.

## What happened in the recorded study?

Each of three campaigns started with the same baseline and fresh agent history. The first request contained only baseline evidence; it did not include the three hand-prepared improved configurations used in the separate memory walkthrough.

| Campaign | Model calls | Proposals tested | Invalid proposals | Starting success | Selected success |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 4 | 3 | 0 | 13/20 | 20/20 |
| 2 | 4 | 3 | 0 | 13/20 | 20/20 |
| 3 | 3 | 2 | 0 | 13/20 | 20/20 |

In campaign 1:

1. Luna enabled subject and date filtering. Python measured an improvement from 13/20 to 19/20 passing scenarios.
2. Luna proposed deduplication. Answers stayed at 19/20 while mean stored records fell from 1.70 to 1.60.
3. Luna lowered the storage-confidence threshold from 0.7 to 0.6. The remaining useful preference was retained, bringing success to 20/20 and mean storage to 1.65 records.
4. Luna returned a stop decision because it had no further supported change to propose from the supplied evidence.

All three agents chose to stop within the four-decision limit. Their final settings matched, but the paths differed: campaign 3 combined deduplication and the lower threshold in decision 2, then stopped on decision 3. A stop decision is not proof of a globally optimal configuration.

The estimated cost of the 11 model calls was **$0.034123**, against a **$0.50** budget. This estimate uses recorded usage and the published Luna rates checked on September 9, 2026. It includes cache-write surcharges and ignores cache-read discounts; it is not an invoice. Local CPU, hardware, and development costs are separate.

**20/20 is a result on these public development stories.** It does not establish production quality, unseen-task performance, or an advantage over human or classical search.

## What is a campaign, an iteration, or a scenario?

- A **campaign** is one complete attempt to improve the baseline, with fresh agent history.
- An **iteration** is one model decision: propose a change or stop. A proposal can be rejected before evaluation.
- A **candidate** is a configuration of the same Python memory tool. Its **parent** is the configuration it changes.
- A **scenario** is a complete test story. It starts with empty memory and contains events: `write`, `query`, or `delete`.
- An **event** is one action. The future-move story writes Berlin, writes future Paris, asks for January 5, and asks for January 12.

A new configuration runs the 20 scenarios **once**. The runner reuses verified deterministic parent evidence for comparisons. Repeating the same memory test would add no answer-quality evidence. We repeat the agent's entire campaign because its decisions can vary.

## Where is the LLM, and where is it absent?

| Component | What executes |
| --- | --- |
| Outer proposer | Luna receives traces and feedback, then returns an SGR decision record. |
| Proposal validation | Python checks structure, permitted settings, event references, and duplicate configurations. |
| Memory tool | Ordinary Python stores prepared facts and selects values from records. |
| Evaluator | Python checks expected answers, state, owner isolation, deletion, and prohibited writes. |
| Browser | JavaScript displays saved evidence. No API key or provider call. |

The memory tool does not extract facts from conversation or generate natural-language answers. The test supplies `city = Paris`, its date, owner, and other fields as JSON. The code copies those fields into an in-memory list and retrieves a value. See [the concrete input and storage walkthrough](docs/memory-tool.md#what-exactly-goes-into-the-program).

**Confidence decides whether a proposed fact is stored.** It is a supplied test score, not a model-calibrated probability. The writer rejects scores below `min_confidence`. A `delivery = courier` proposal scored `0.4` is rejected at threshold `0.7` and stored at `0.2`. The agent's successful `0.6` threshold admits a useful preference scored `0.6` while keeping the uncertain `0.4` proposal out.

## What the agent is allowed to change

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

## Run a new live campaign

Put this in your local `.env.local`, replacing the placeholder with your key:

```dotenv
OPENAI_API_KEY=your-key
```

The file is ignored by Git. Do not put the key in the browser or publish it with a static site.

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

## What is saved, and what does “selected” mean?

Each iteration saves the exact request (including instructions and schema), provider response, usage, timing, validation result, and completed Python evaluation. Evaluation folders contain traces, state changes, metrics, and file hashes. The root manifest covers every saved file and identifies the source used for the study.

A new parent must pass every hard check and either improve complete-scenario success or preserve that score while using fewer stored records. A rejected change leaves the previous parent intact. The next request receives the proposal's outcome either way.

**Selected means selected for continued experimentation.** It does not authorize a production release. Human adoption review remains separate; the existing `lab decision` command records a review but does not deploy anything.

The 20 stories are public development cases. The original `search`, `evaluation`, and `adversarial` labels organize them but provide no hidden holdout. A coding agent with independent filesystem access would need a separate sandbox; this model is restricted by the capabilities actually provided to its API call.

## Verify and navigate the code

```sh
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen ruff check lab tests
uv run --frozen ruff format --check lab tests
uv run --frozen python -m lab verify artifacts/agent-study-02 --source
uv run --frozen python -m lab verify artifacts/article-01.5 --source
node --check web/campaign.js
```

Tests use scripted transport to check the real iteration controller without provider calls. They cover feedback, failed-reference validation, parent selection, a regressing change, budget exhaustion, provider errors, strict schema requirements, cost accounting, and the existing memory checks.

| File | Responsibility |
| --- | --- |
| [lab/agent.py](lab/agent.py) | SGR models, instructions, permissions, API request, and token-cost accounting. |
| [lab/campaign.py](lab/campaign.py) | Fresh campaigns, feedback, selection, budgets, and the campaign ledger/report. |
| [lab/memory.py](lab/memory.py) | The deterministic tool: writes, validity history, retrieval, and deletion. |
| [lab/runner.py](lab/runner.py) | Fixed scoring, comparison, evidence export, and verification. |
| [lab/__main__.py](lab/__main__.py) | CLI commands and static export. |
| [web/index.html](web/index.html), [web/campaign.js](web/campaign.js) | Agent-campaign explorer. |
| [web/memory.html](web/memory.html), [web/app.js](web/app.js) | Detailed memory-mechanics explorer. |

The [development run log](docs/experiment-notes.md) distinguishes the pilot from the recorded three-campaign study and explains the preserved older deterministic snapshots. Those snapshots are evidence of their own runs, not new LLM measurements.
