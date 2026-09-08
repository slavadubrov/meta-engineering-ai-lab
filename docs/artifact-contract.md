# Public artifact contract, version 1.0

Python is authoritative. The browser reads `../artifacts/article-01.2/bundle.json`
from `web/index.html`; it filters recorded evidence, never evaluates a target.
`report.html` is a semantic, standalone no-JavaScript comparison; `report.md`
contains the same conclusions. `manifest.json` hashes every public artifact.
The original normalized scenarios and candidate proposals ship with the code.

```text
bundle
  schema_version, release_id, generated_at, reproduction_command
  disclosures[], limitations[], provenance{}, links{article,source,release}
  metric_definitions{metric: {label,unit,description,direction}}
  scenarios[{id,family,role,title,description}]
  blocked_proposals[{id,patch,error,status}]
  candidates[]
    id, label, parent_id, hypothesis, predicted_effect
    proposer{type,name,model,prompt_version}, config{}, budget{}
    changes[{field,before,after}]
    summary
      metrics{metric: number|null}
      repeat_count, task_count
      role_metrics{search|evaluation|adversarial: {metrics...}}
      hard_constraints{name: {passed,violations,checks}}
      paired{parent_id,task_count,wins,ties,losses,mean_delta,repeat_deltas[]}
    recommendation{status,rationale}
    decision{status,actor,rationale}
    runs[] (first repeat, all scenarios; every repeat is in runs.jsonl)
      scenario_id, family, role, title, description, repeat, success
      expected[], actual[], metrics{}, hard_constraints{}
      before[], after[], state_diff{added[],removed[],changed[]}
      trace[]
        step, action, detail, result, before[], after[], state_diff{}
        retrieved_ids[], packed_ids[], answer (query steps only)
```

Memory records contain `id`, `tenant`, `user`, `entity`, `key`, `value`,
`valid_from`, `valid_to` (null means open), `confidence`, `source`, and
`observed_at`, and `source_event_id` (scenario ID plus the original write step).
Trace dates are synthetic calendar dates. Changed state entries
are `{id,before,after}`; before and after are complete records.

Every decision initially has `status: "pending_human_review"`, `actor: null`.
Recommendations use `retain_baseline`, `recommend_accept`, or
`recommend_reject`. A recommendation is not authorization or a human decision.
An interactive rehearsal may show accept/reject only as a clearly labeled
local simulation. Never overwrite the authoritative `decision` from the UI.

`links.article`, `links.source`, and `links.release` are null until published.
Do not invent URLs or display null links. The local reproduction command is
usable immediately. All scenarios are synthetic, public, and visible during
authorship. Their roles organize diagnostic/regression checks; there is no
blind held-out evaluation. Repeats check determinism and measure local timing;
they are not independent stochastic trials or evidence of generalization.

Latency is measured local CPU execution of a tiny deterministic scenario, not
LLM service latency. Context words are whitespace counts, not model tokens.
LLM calls and token use are zero; monetary cost is zero provider expenditure,
excluding local hardware, energy, and authoring effort.
