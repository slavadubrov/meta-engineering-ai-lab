const $ = (id) => document.getElementById(id);
const layers = ["answers", "state", "audit", "previous_suite", "budgets"];
// Splits whose unwanted writes each layer checks: development, audit, previous suite.
const checkedWrites = { answers: 0, state: 1, audit: 2, previous_suite: 3, budgets: 3 };
const descriptions = {
  answers: "The 8/8 score rewards answering these questions and ignores what memory stores. Four candidates tie at 8/8; the declared order picks the first.",
  state: "Both 0.2 candidates fail because they store the unwanted guesses. Threshold 0.4 rejects the 0.3 guesses and still answers 8/8, so it becomes the apparent winner.",
  audit: "Threshold 0.4 stores an uncertain 0.5 city update and answers 6/12. Threshold 0.6 answers 12/12 with no unwanted writes. Threshold 0.7 rejects the update but also drops a useful 0.6 preference.",
  previous_suite: "The 20 Part 1 scenarios return, with owner isolation, deletion and prohibited-write checks. The 0.2 and 0.4 candidates fail this suite too, so it alone would already reject them.",
  budgets: "The last layer adds a budget of 3 context words per query and 10 ms local p95 per scenario. Threshold 0.2 with k=3 also exceeds the context budget.",
};
const arms = {
  exact: "Exact match",
  exact_with_constraints: "Exact match + hard checks",
  jev_answer_only: "Jev, answer only",
  jev_with_constraints: "Jev + hard checks",
  jev_state_aware: "Jev, given state evidence",
};
function cells(values) {
  const tr = document.createElement("tr");
  for (const value of values) {
    const td = document.createElement("td");
    td.textContent = value;
    tr.append(td);
  }
  return tr;
}
const ratio = (split) => `${split.passes}/${split.scenarios}`;
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

function showStudy(study) {
  if (study.version !== "jev-comparison-v2" || !Array.isArray(study.cases) || study.cases.length > 100 || !study.arms) {
    throw new Error("Unsupported comparison format.");
  }
  const verdict = (value) => (value === true ? "accept" : value === false ? "reject" : "not run");
  $("jev-summary").replaceChildren(...Object.entries(arms).filter(([id]) => study.arms[id]).map(([id, label]) => {
    const s = study.arms[id].score;
    return cells([label, s.reference, `${s.agreement}/${s.total}`, `${s.false_accepts}/${s.negative_cases}`, `${s.false_rejects}/${s.positive_cases}`]);
  }));
  $("jev-cases").replaceChildren(...study.cases.map((c) => cells([
    c.id, c.category, verdict(c.semantic_accept), verdict(c.reference_accept),
    ...Object.keys(arms).map((id) => verdict(study.arms[id]?.predictions?.[c.id])),
  ])));
  const calls = (study.calls ?? []).map((c) => `${c.name}: ${c.status}${typeof c.elapsed_s === "number" ? `, ${c.elapsed_s.toFixed(2)} s` : ""}${c.cost_usd == null ? "" : `, $${c.cost_usd.toFixed(6)}`}`);
  $("jev-status").textContent = `${study.model}: ${study.status}. Billed cost: ${study.cost_usd == null ? "unknown" : `$${study.cost_usd.toFixed(6)}`}. ${calls.join(" · ")}`;
}

$("jev-file").addEventListener("change", async (event) => {
  try {
    const file = event.target.files[0];
    if (!file) return;
    if (file.size > 1_000_000) throw new Error("Comparison exceeds 1 MB.");
    showStudy(JSON.parse(await file.text()));
  } catch (error) {
    $("jev-summary").replaceChildren();
    $("jev-cases").replaceChildren();
    $("jev-status").textContent = error.message;
  }
});

try {
  const responses = await Promise.all([
    fetch("../reports/article-02/grid/bundle.json"),
    fetch("../reports/article-02/jev/study.json"),
  ]);
  if (responses.some((r) => !r.ok)) throw new Error("Evidence could not be loaded. Start the local server with: uv run --frozen python -m lab serve --port 8075");
  const [bundle, study] = await Promise.all(responses.map((r) => r.json()));
  if (bundle.schema_version !== 2 || !Array.isArray(bundle.candidates)) throw new Error("Unsupported evidence format.");
  const byId = new Map(bundle.candidates.map((row) => [row.id, row]));
  const splits = ["development", "audit", "regression"];
  function render() {
    const layer = $("layer").value;
    const rows = bundle.rankings[layer].map((id) => byId.get(id));
    const first = rows.find((row) => row.rejections[layer].length === 0);
    $("winner").textContent = first ? `${layer === "answers" ? "Answer-only winner" : "First candidate that passes"}: ${first.id}` : "No candidate passes these checks";
    $("explanation").textContent = descriptions[layer];
    const d = bundle.decision;
    $("adoption").textContent = layer === "budgets"
      ? `Decision: ${d.outcome}. ` + d.eligible_challengers.map((c) => `${c.id} passes every check but has ${c.wins} wins and ${c.losses} losses against the incumbent.`).join(" ")
      : "";
    $("next").disabled = layer === "budgets";
    const index = layers.indexOf(layer);
    $("ranking").replaceChildren(...rows.map((r) => cells([
      r.id + (r.id === d.incumbent ? " (incumbent)" : ""),
      ratio(r.development),
      checkedWrites[layer] ? splits.map((s, i) => (i < checkedWrites[layer] ? r[s].state_violations : "—")).join(" / ") : "Not checked",
      index < 2 ? "Not checked" : ratio(r.audit),
      index < 3 ? "Not checked" : ratio(r.regression),
      r.rejections[layer].join("; ") || "none",
    ])));
  }
  $("layer").addEventListener("change", render);
  $("next").addEventListener("click", () => {
    $("layer").value = layers[Math.min(layers.length - 1, layers.indexOf($("layer").value) + 1)];
    render();
  });
  $("paired").replaceChildren(...bundle.candidates.map((r) => {
    const wlt = (group) => { const g = r.vs_incumbent[group]; return `${g.wins}-${g.losses}-${g.ties}`; };
    return cells([
      r.id, wlt("audit: uncertain-city-update"), wlt("audit: useful-0.6-preference"),
      splits.map((s) => r[s].mean_context_words.toFixed(2)).join(" / "),
      Math.max(...splits.map((s) => r[s].p95_ms)).toFixed(3),
    ]);
  }));
  $("frontier").textContent = `Pareto frontier on audit answers and context words, among candidates that pass the previous suite: ${bundle.pareto_frontier.join(", ")}.`;
  let step = 0;
  function showEvent() {
    const event = bundle.example.trace[step];
    $("event-number").textContent = `${step + 1} / ${bundle.example.trace.length}`;
    $("event-title").textContent = `Event ${event.step}: ${event.action}`;
    if (event.action === "write") {
      const fact = event.detail.fact;
      const state = event.detail.should_retain ? "" : same(event.before, event.after) ? " State check: passes, memory unchanged." : " State check: fails, memory changed.";
      $("event-text").textContent = `${fact.key} = ${fact.value}; supplied confidence ${fact.confidence}; should retain: ${event.detail.should_retain}. Result: ${event.result.status}.${state}`;
    } else if (event.action === "query") {
      const passed = event.result.answer === event.detail.expected;
      $("event-text").textContent = `Expected: ${event.detail.expected ?? "no answer"}. Answer: ${event.result.answer ?? "no answer"}. Answer check: ${passed ? "passes" : "fails"}.`;
    } else {
      $("event-text").textContent = `Delete ${event.detail.entity}/${event.detail.key}. Result: ${event.result.status}.`;
    }
    $("state").textContent = event.after.map((r) => `${r.id}: ${r.key} = ${r.value}`).join("\n") || "Empty";
    $("previous-event").disabled = step === 0;
    $("next-event").disabled = step === bundle.example.trace.length - 1;
  }
  $("previous-event").addEventListener("click", () => { step--; showEvent(); });
  $("next-event").addEventListener("click", () => { step++; showEvent(); });
  $("provenance").textContent = `Evidence version: ${bundle.contract.version}. ${bundle.executions} scenario runs. Source hashes are in bundle.json.`;
  render();
  showEvent();
  showStudy(study);
} catch (error) {
  $("error").hidden = false;
  $("error").textContent = error.message;
  $("winner").textContent = "Evidence unavailable";
  $("next").disabled = true;
}
