# LLM memory improvement campaigns

The outer agent proposes changes; deterministic Python measures them. Every campaign starts from the same baseline with fresh history.

Model: `gpt-5.6-luna`. Prompt: `memory-improver-sgr-v1`.

| Campaign | Outcome | Selected success | Model calls |
| --- | --- | ---: | ---: |
| campaign-01 | iteration_limit | 95% | 1 |

## campaign-01 / iteration 1

Status: **evaluated**. Parent: `baseline`.

[Exact request](campaign-01/iteration-01/request.json) · [Recorded outcome](campaign-01/iteration-01/result.json)

Patch: `{"filter_entity": true, "time_aware": true}`.

Success: 95%. Selected for next iteration: True.

[Proposal](campaign-01/iteration-01/proposal.json) · [Evaluation](campaign-01/iteration-01/evaluation/report.html)

## Limits and cost

All 20 stories are public development inputs. These campaigns do not establish held-out generalization or an advantage over manual tuning.

Estimated model cost (cache discounts ignored): $0.004372. Cost plus unknown-call reservations: $0.004372. Provider failures remain in the record; unknown cost is not zero.

Selection only changes the next experimental parent. Nothing is deployed; human release review is still required.
