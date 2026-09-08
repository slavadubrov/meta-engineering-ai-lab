# Research for article 1: from traces to better memory

Verified on 2026-09-07. This is a source synthesis and experimental-design note,
not a report of running the cited benchmarks. The companion's generated run
artifacts are the authority for its own results. Paper versions, claim scope,
and exclusions are recorded in [source-ledger.csv](source-ledger.csv).

## The claim this first article can earn

A small memory subsystem can make improvement experiments inspectable: freeze
the tasks and evaluator, change one bounded policy, replay from a clean state,
and retain the evidence for a human promotion decision.

This is a narrower question than whether agents outperform engineers at
research. The first article establishes the experiment contract. Equal-budget
comparisons of human, random, optimizer, and agent proposals belong to the later
search-strategy article.

The project uses synthetic multi-user memory, successful and negative
candidates, reproducible evidence, human review, and an interactive explorer
of frozen results. Python owns the calculations; the website lets readers
inspect the exported evidence. A live LLM backend is not required.

## What transfers from the research

| Source                                                                                                                            | Verified mechanism or evaluation scope                                                                                                      | Transfer to this lab                                                                                       | Limit                                                                                                                                                                                                      |
| --------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [autoresearch, pinned program](https://github.com/karpathy/autoresearch/blob/228791fb499afffb54b46200aca536f79142f117/program.md) | One editable training file, a protected evaluation file, fixed five-minute training budget, and keep/discard/crash records.                 | Explicit change boundary, baseline first, bounded run, failed-candidate retention.                         | Training time excludes startup and compilation. Instructions are not an OS sandbox, and keep-on-score is not proof of generalization. Our human promotion step is an adaptation.                           |
| [Meta-Harness v1](https://arxiv.org/html/2603.28052v1)                                                                            | A coding proposer selectively reads prior candidate code, scores, and traces through a filesystem.                                          | Keep navigable per-candidate history with enough evidence to diagnose a failure.                           | Section 4.3 uses the same TerminalBench-2 tasks for search and final evaluation; that result is not held-out generalization. Appendix D labels its advice engineering experience, not scientific findings. |
| [LongMemEval v2](https://arxiv.org/html/2410.10813v2)                                                                             | Extraction, multisession reasoning, temporal reasoning, knowledge updates, and abstention; distinguishes retrieval from downstream reading. | Include current-value, historical-value, missing-evidence, and distractor scenarios.                       | Uses an LLM correctness judge with human meta-evaluation. Its original model scores do not describe current products or this deterministic target.                                                         |
| [LoCoMo](https://arxiv.org/abs/2402.17753v1)                                                                                      | Persona/event-grounded long conversations produced by a machine-human pipeline; QA, summarization, and multimodal dialogue tasks.           | Make source events and temporal continuity visible in the trace.                                           | Our small structured fixtures do not reproduce its conversational length, multimodal setting, or language difficulty.                                                                                      |
| [MemoryAgentBench v4](https://arxiv.org/html/2507.05257v4)                                                                        | Incremental interactions test retrieval, test-time learning, long-range understanding, and selective forgetting.                            | Evaluate after updates, not only against a static final memory dump.                                       | Its conflict-consolidation task prioritizes later information. This selective-forgetting score is not a physical-erasure or deletion-compliance test.                                                      |
| [VehicleMemBench v1](https://arxiv.org/abs/2603.23840v1)                                                                          | Multi-user memory and tool use are evaluated by comparing post-action environment state with a target state.                                | Check structured outcomes directly when the environment makes them observable.                             | Its vehicle simulator is domain-specific. Deterministic checks validate the stated contract, not every desirable behavior.                                                                                 |
| [GroupMemBench v2](https://arxiv.org/abs/2605.14498v2)                                                                            | Group conversation structure, speaker-grounded beliefs, and asker-dependent questions are explicit.                                         | Ground records in a subject and the authenticated actor; test another user's statement about that subject. | Separate tenant IDs alone do not implement group dialogue understanding or role-specific language.                                                                                                         |
| [GateMem v1](https://arxiv.org/abs/2606.18829v1)                                                                                  | Evaluates legitimate utility, contextual authorization boundaries, and active forgetting after deletion.                                    | Keep legitimate-use tests beside forbidden-read and deletion tests.                                        | Agent-facing forgetting is narrower than erasing backups, logs, exports, or every derived copy.                                                                                                            |
| [MemoryGraft v1](https://arxiv.org/abs/2512.16962v1)                                                                              | Poisoned past experiences can influence later agent behavior after retrieval.                                                               | Test a malicious source event, the resulting stored state, and a later query.                              | Reported attacks use a particular MetaGPT DataInterpreter/GPT-4o setup; no attack rate transfers to this lab.                                                                                              |
| [MemSecBench v1](https://arxiv.org/abs/2607.27080v1)                                                                              | Tracks write, execution, and forgetting with deterministic checks, judge-model assessments, and programmatic gates.                         | Separate persistence from downstream use and selective repair.                                             | A successful write-time check alone does not prove safe later behavior. Its results depend on the tested configurations and judges.                                                                        |

Two engineering accounts help explain the method without adding a framework.
[Anthropic's eval guide](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
distinguishes a task, repeated trials, transcript, and environment outcome. It
also distinguishes deterministic grading from calibrated model grading. This
supports checking memory state rather than trusting a final answer that says
the change was made. [OpenAI's harness engineering account](https://openai.com/index/harness-engineering/)
describes repository knowledge, executable feedback, and mechanically enforced
boundaries in one team's development setting. Use it as engineering precedent,
not as a measured productivity effect for this project.

The freshest paper found in this pass,
[CAPTURE v1, submitted 2026-09-02](https://arxiv.org/abs/2609.02265v1),
studies genuine preference changes versus poisoning and temporary context.
It is an early preprint, under review. It motivates a limitation: a newest-first
rule cannot decide whether an untrusted new assertion should become truth. Its
model and numerical results are not needed for article 1.

## Introduce the whole system before the worked trace

The article introduces the general improvement system and the six-part series
before the memory case. The worked trace then uses a synthetic support assistant:
a reported move is not yet effective, but the baseline answers with the future
city. Incoming events, state versions, retrieved records, and the actual answer
make the difference between observation time and validity time inspectable.

Do not call this a captured production incident. Do not describe prestructured
input fields as LLM extraction. If the offline target uses a deterministic
parser, show the supported grammar and call it a controlled stand-in for the
extraction boundary. The contribution is the experiment around that target.

The author's existing articles supply the bridge:

- [AI Agent Memory: Schema-Guided State and Provenance](https://slavadubrov.com/blog/2026/06/20/schema-guided-agent-memory/) separates model-proposed state from application-owned lifecycle rules.
- [AI Agent Evaluation in Production: Traces to Test Suites](https://slavadubrov.com/blog/2026/06/10/agent-evals-traces-to-test-suites/) turns observed failures into versioned cases with outcome and trajectory checks.
- [Harness Engineering for AI Agents: Designing Control Loops](https://slavadubrov.com/blog/2026/07/22/ai-agent-harness-engineering/) assigns authority to the code that enforces acceptance and measures one intervention at a time.

These connections were checked against the current local source articles. They
are narrative continuity, not independent evidence that this lab works.

## Recommended experiment contract

The following is design guidance for this project, not a benchmark requirement
or an industry standard.

**Mutable policy:** a small set of validated memory-policy values, such as
current-versus-append behavior, relevance ranking, and retrieval count. Keep
tenant isolation, trusted actor scope, prohibited writes, and promotion
authority outside the proposal surface. A deliberately unsafe negative control
may be a separately authored fixture; label it as such, rather than quietly
making security negotiable.

**Fixed evidence:** scenario definitions, expected state, evaluator, comparison
baseline, timeout, repetition policy, and exported artifact schema. A manifest
describing these as immutable is only a declaration. A runner can reject changed
hashes or unsupported keys. Arbitrary untrusted candidate code additionally
requires filesystem, process, secret, and network containment; fresh Python
objects or a subprocess alone do not provide that security boundary.

**State isolation:** every candidate/trial starts with a fresh target instance
and the same scenario state. Never reuse a preceding candidate's warmed memory.
Preserve raw per-task results before aggregation, including errors and timeouts.

**Promotion:** evaluation emits evidence and eligibility. A separate explicit
decision records accept/reject, reviewer, rationale, and the exact candidate
artifact digest. An automated passing grade must not create a fictional human
approval. If the author has not reviewed the run, record it as pending review or
as a clearly illustrative decision.

### Keep the three evaluation roles honest

| Role               | What the proposer can use                                                                           | What a score establishes                                                   |
| ------------------ | --------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Search/development | Full task evidence and prior failed runs                                                            | Whether a change helps on cases that influenced it.                        |
| Held-out           | No task content, answer keys, or per-case feedback while proposing                                  | Additional evidence only if access and iteration were actually separated.  |
| Adversarial        | The policy boundary can be documented; keep attack instances outside adaptive search where possible | Whether these particular isolation, deletion, and poisoning checks passed. |

A committed public teaching suite can demonstrate these roles. It cannot prove
the authors or the coding agent never saw its held-out cases. Name that limit
in the article and the UI. Once held-out results are used to diagnose or choose
the next candidate, that set becomes development evidence; reserve a fresh
suite for a later confirmatory comparison. For this small lab, fixed counts and
capability coverage are more informative than an impressive-looking split
percentage.

### Candidates worth preserving

1. A current-value fix with a prediction about stale-state failures.
2. A plausible ranking or retrieval-count change that produces no useful gain.
3. A regression, such as truncating context before collecting all required facts.
4. A proxy trap: retrieve more relevant facts while also adding stale or
   distracting facts that worsen the downstream answer.

These are candidate ideas, not claimed outcomes. Report what the implementation
actually produces. A fixture designed to fail demonstrates the evaluator's
coverage; it is not an independently discovered research result. Record proposal
origin accurately: human-authored, coding-agent-authored, or a live proposer call
with its actual model/prompt and response. Handwritten JSON must not be presented
as an output from a model that was never called.

## Measurement and lineage

Show denominators and metric definitions. Use downstream case success as the
main outcome, with current-state correctness, unnecessary/prohibited writes,
relevant retrieval, distractors, stale use, deletion, and cross-user leakage as
diagnostics or hard checks. Distinguish correct abstention from a missing answer.
Any zero-denominator precision/recall result should be explicitly unavailable
or follow a documented convention, never silently imply perfect quality.

A source ID links a stored fact to its input event. An experiment ID links a
candidate to its parent and observed effects. Preserve both: they answer
different questions. An inspectable record needs the hypothesis, predicted
effect, diff, parent, target and evaluator versions, dataset digest, model/prompt
identity where used, initial/final states, per-step trace, trial results,
resource measurements, and decision. A hash demonstrates content identity; it
does not authenticate authorship or make a writable file immutable.

For a deterministic offline run, report model calls and model-token usage as
zero. Do not call a character or whitespace estimate real model tokens. Report
context bytes/words or label an approximation. Zero API spend excludes the
authoring agent, engineering time, hardware, and electricity. Record measured
wall time and the host/runtime identity; p50/p95 on tiny local operations are
descriptive and not a service latency claim.

Repeating the same deterministic fixtures can check reproducibility and latency
variation. It does not create new task evidence or establish stochastic model
reliability. For a future live model, predeclare paired task/trial counts, model
settings, budgets, error handling, and uncertainty analysis. No source supplies
a universal number of repetitions that makes a small gain credible.

Public-safe synthetic artifacts can include complete state diffs. Real data
requires an explicit artifact retention policy: deleting the target record
while keeping its value in a trace or exported snapshot is not complete data
erasure. Avoid making deletion-compliance claims for this demonstration.

## What the earlier reports do and do not support

Earlier unpublished research notes served as discovery maps. Their core
distinction between a bounded improvement
experiment and recurring operational automation survives primary-source checks.
Their embedded citation tokens and numbered source lists are not proof by
themselves.

Do not reuse their claims about universal framework superiority, production
readiness, coder productivity multipliers, worktrees guaranteeing isolation,
or autonomous superiority. Do not describe autoresearch's score ratchet as a
guarantee of monotonic real-world quality. The March 2026 pinned program keeps
`results.tsv` untracked; the lab should retain its own failed artifacts
deliberately rather than claim Git automatically preserves everything.

The existing memory-refresh research correctly warns against treating a
database choice as a lifecycle implementation. This article should retain that
boundary. No new vector database, orchestration framework, trained model, or
live backend is necessary to answer article 1's question. These are extension
choices to evaluate against the same contract later.

The ending should hand one concrete question to article 2: after the loop has
made more experiments easy to run, what prevents it from optimizing an
incomplete evaluator?
