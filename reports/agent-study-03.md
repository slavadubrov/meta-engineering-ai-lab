# LLM memory improvement campaigns

Full requests, traces, state changes, and file manifests are in the [evidence archive](https://github.com/slavadubrov/meta-engineering-ai-lab/releases/download/v0.2.1/memory-experiment-evidence.tar.gz). From the repository, run `uv run --frozen python scripts/fetch_evidence.py` to restore them under `artifacts/`. [Archive checksum and retained examples](evidence.json).

The outer agent proposes changes; deterministic Python measures them. Every campaign starts from the same baseline with fresh history.

Model: `gpt-5.6-luna`. Prompt: `memory-improver-sgr-v2`.

| Campaign | Outcome | Selected success | Model calls |
| --- | --- | ---: | ---: |
| campaign-01 | agent_stopped | 100% | 4 |
| campaign-02 | agent_stopped | 100% | 4 |
| campaign-03 | agent_stopped | 100% | 4 |

## campaign-01 / iteration 1

Status: **evaluated**. Parent: `baseline`.

[Exact request](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-01/iteration-01/request.json) · [Recorded outcome](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-01/iteration-01/result.json)

Patch: `{"filter_entity": true, "time_aware": true}`.

Success: 95%. Selected for next iteration: True.

[Proposal](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-01/iteration-01/proposal.json) · [Evaluation](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-01/iteration-01/evaluation/report.html)

## campaign-01 / iteration 2

Status: **evaluated**. Parent: `agent-01`.

[Exact request](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-01/iteration-02/request.json) · [Recorded outcome](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-01/iteration-02/result.json)

Patch: `{"deduplicate": true}`.

Success: 95%. Selected for next iteration: True.

[Proposal](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-01/iteration-02/proposal.json) · [Evaluation](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-01/iteration-02/evaluation/report.html)

## campaign-01 / iteration 3

Status: **evaluated**. Parent: `agent-02`.

[Exact request](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-01/iteration-03/request.json) · [Recorded outcome](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-01/iteration-03/result.json)

Patch: `{"min_confidence": 0.6}`.

Success: 100%. Selected for next iteration: True.

[Proposal](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-01/iteration-03/proposal.json) · [Evaluation](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-01/iteration-03/evaluation/report.html)

## campaign-01 / iteration 4

Status: **agent_stopped**. Parent: `agent-03`.

[Exact request](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-01/iteration-04/request.json) · [Recorded outcome](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-01/iteration-04/result.json)

## campaign-02 / iteration 1

Status: **evaluated**. Parent: `baseline`.

[Exact request](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-02/iteration-01/request.json) · [Recorded outcome](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-02/iteration-01/result.json)

Patch: `{"filter_entity": true, "time_aware": true}`.

Success: 95%. Selected for next iteration: True.

[Proposal](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-02/iteration-01/proposal.json) · [Evaluation](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-02/iteration-01/evaluation/report.html)

## campaign-02 / iteration 2

Status: **evaluated**. Parent: `agent-01`.

[Exact request](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-02/iteration-02/request.json) · [Recorded outcome](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-02/iteration-02/result.json)

Patch: `{"deduplicate": true}`.

Success: 95%. Selected for next iteration: True.

[Proposal](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-02/iteration-02/proposal.json) · [Evaluation](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-02/iteration-02/evaluation/report.html)

## campaign-02 / iteration 3

Status: **evaluated**. Parent: `agent-02`.

[Exact request](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-02/iteration-03/request.json) · [Recorded outcome](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-02/iteration-03/result.json)

Patch: `{"min_confidence": 0.6}`.

Success: 100%. Selected for next iteration: True.

[Proposal](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-02/iteration-03/proposal.json) · [Evaluation](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-02/iteration-03/evaluation/report.html)

## campaign-02 / iteration 4

Status: **agent_stopped**. Parent: `agent-03`.

[Exact request](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-02/iteration-04/request.json) · [Recorded outcome](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-02/iteration-04/result.json)

## campaign-03 / iteration 1

Status: **evaluated**. Parent: `baseline`.

[Exact request](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-03/iteration-01/request.json) · [Recorded outcome](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-03/iteration-01/result.json)

Patch: `{"filter_entity": true, "time_aware": true}`.

Success: 95%. Selected for next iteration: True.

[Proposal](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-03/iteration-01/proposal.json) · [Evaluation](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-03/iteration-01/evaluation/report.html)

## campaign-03 / iteration 2

Status: **evaluated**. Parent: `agent-01`.

[Exact request](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-03/iteration-02/request.json) · [Recorded outcome](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-03/iteration-02/result.json)

Patch: `{"deduplicate": true}`.

Success: 95%. Selected for next iteration: True.

[Proposal](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-03/iteration-02/proposal.json) · [Evaluation](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-03/iteration-02/evaluation/report.html)

## campaign-03 / iteration 3

Status: **evaluated**. Parent: `agent-02`.

[Exact request](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-03/iteration-03/request.json) · [Recorded outcome](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-03/iteration-03/result.json)

Patch: `{"min_confidence": 0.6}`.

Success: 100%. Selected for next iteration: True.

[Proposal](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-03/iteration-03/proposal.json) · [Evaluation](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-03/iteration-03/evaluation/report.html)

## campaign-03 / iteration 4

Status: **agent_stopped**. Parent: `agent-03`.

[Exact request](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-03/iteration-04/request.json) · [Recorded outcome](https://github.com/slavadubrov/meta-engineering-ai-lab/blob/v0.2.1/artifacts/agent-study-03/campaign-03/iteration-04/result.json)

## Limits and cost

All 20 stories are public development inputs. These campaigns do not establish held-out generalization or an advantage over manual tuning.

Estimated model cost (cache-write surcharge included; read discounts ignored): $0.039177. Cost plus unknown-call reservations: $0.039177. Provider failures remain in the record; unknown cost is not zero.

Selection only changes the next experimental parent. Nothing is deployed; human release review is still required.
