const $ = (id) => document.getElementById(id);
const layers = ["proxy", "state", "audit", "assurance", "all"];
const descriptions = {
  proxy: "The 8/8 score rewards answering these questions. It ignores four unwanted state changes. Four candidates tie at 8/8; the declared tie-break selects the first.",
  state: "The 0.2 threshold is rejected for storing unwanted facts. Threshold 0.4 still answers 8/8 and avoids the development guesses, so it becomes the apparent winner.",
  audit: "Threshold 0.4 accepts higher-confidence guesses in the audit cases and answers only 6/12 correctly. Threshold 0.6 passes 12/12 while preserving the state requirement.",
  assurance: "The complete previous suite is back in the decision, including owner isolation, deletion and prohibited writes. Threshold 0.6 also passes its 20/20 scenarios. Hard violations are independent rejection reasons.",
  all: "The policy now includes a mean context budget of 3 words/query, local p95 of 10 ms, and zero provider spend. These are demonstration budgets, not production service objectives. Inspect the recorded timing before making a decision.",
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
function ratio(row) { return `${row.successes}/${row.scenarios}`; }
function percent(value) { return `${(100 * value).toFixed(1)} pp`; }
$("jev-file").addEventListener("change", async (event) => {
  $("jev-summary").replaceChildren();
  $("jev-cases").replaceChildren();
  $("jev-costs").textContent = "";
  try {
    const file = event.target.files[0];
    if (!file) return;
    if (file.size > 1_000_000) throw new Error("Comparison exceeds 1 MB.");
    const study = JSON.parse(await file.text());
    if (study.version !== "jev-comparison-v1" || !Array.isArray(study.cases) || study.cases.length > 100 || !study.arms) throw new Error("Unsupported comparison format.");
    const methods = {exact: "Exact — semantic", exact_with_constraints: "Exact + constraints — behavior", jev_answer_only: "Jev — semantic", jev_with_constraints: "Jev + constraints — behavior", jev_state_aware: "Jev state-aware — behavior"};
    const rows = Object.entries(methods).filter(([id]) => study.arms[id]).map(([id, label]) => {
      const arm = study.arms[id];
      const m = arm.semantic ?? arm.behavior ?? arm.agreement;
      return cells([label, `${m.agreement}/${m.total}`, `${m.false_accepts}/${m.negative_cases}`, `${m.false_rejects}/${m.positive_cases}`]);
    });
    const verdict = (value) => value === true ? "Accept" : value === false ? "Reject" : "Not measured";
    const cases = study.cases.map((c) => cells([
      c.id, verdict(c.semantic_accept), verdict(c.reference_accept),
      ...["exact", "jev_answer_only", "jev_with_constraints", "jev_state_aware"].map((id) => verdict(study.arms[id]?.predictions?.[c.id])),
    ]));
    $("jev-summary").replaceChildren(...rows);
    $("jev-cases").replaceChildren(...cases);
    $("jev-costs").textContent = (study.calls ?? []).map((c) => `${c.name}: ${c.status}, ${typeof c.elapsed_s === "number" ? c.elapsed_s.toFixed(3) + " s/request" : "time unmeasured"}, ${c.cost_usd == null ? "cost unknown" : "$" + c.cost_usd}`).join(" · ");
    $("jev-status").textContent = `${study.model}: ${study.status}. Reported cost: ${study.cost_usd == null ? "unknown / unmeasured" : `$${study.cost_usd}`}. Local artifact; provenance and labels require review.`;
  } catch (error) {
    $("jev-status").textContent = error.message;
  }
});
try {
  const responses = await Promise.all([
    fetch("../reports/article-02/bundle.json"),
    fetch("../experiments/evaluator-exploits/judge-cases.json"),
  ]);
  if (responses.some((r) => !r.ok)) throw new Error("Evidence could not be loaded. Serve the repository root over local HTTP.");
  const [bundle, calibration] = await Promise.all(responses.map((r) => r.json()));
  if (bundle.schema_version !== 1 || !Array.isArray(bundle.candidates)) throw new Error("Unsupported evidence format.");
  const byId = new Map(bundle.candidates.map((row) => [row.id, row]));
  function fromHash() {
    const params = new URLSearchParams(location.hash.slice(1));
    $("layer").value = layers.includes(params.get("layer")) ? params.get("layer") : "proxy";
    $("repeats").checked = params.get("repeats") === "1";
    render();
  }
  function render() {
    const layer = $("layer").value;
    const rows = bundle.rankings[layer].map((id) => byId.get(id));
    const eligible = rows.find((row) => row.rejections[layer].length === 0);
    $("winner").textContent = eligible ? `${layer === "proxy" ? "Apparent winner" : "First eligible candidate"}: ${eligible.id}` : "No candidate passes these checks";
    $("explanation").textContent = descriptions[layer];
    $("next").disabled = layer === "all";
    $("ranking").replaceChildren(...rows.map((r) => cells([
      r.id, ratio(r.development), layer === "proxy" ? "Not checked" : r.development.state_violations,
      layers.indexOf(layer) < 2 ? "Not checked" : ratio(r.audit),
      r.rejections[layer].join("; ") || (layer === "proxy" ? "Proxy pass only" : "Eligible under selected checks"),
    ])));
    $("uncertainty").replaceChildren(...bundle.candidates.map((r) => cells([
      r.id, ($("repeats").checked ? r.audit.repeat_scores : r.audit.repeat_scores.slice(0, 1)).map((v) => `${100*v}%`).join(" · "),
      `${percent(r.audit_paired_delta.delta)} [${percent(r.audit_paired_delta.lower)}, ${percent(r.audit_paired_delta.upper)}]`,
      r.audit.mean_context_words.toFixed(2), r.audit.p95_ms.toFixed(3),
    ])));
  }
  function update() {
    const params = new URLSearchParams({layer: $("layer").value, repeats: $("repeats").checked ? "1" : "0"});
    history.replaceState(null, "", `#${params}`);
    render();
  }
  $("layer").addEventListener("change", update);
  $("repeats").addEventListener("change", update);
  $("next").addEventListener("click", () => { $("layer").value = layers[Math.min(4, layers.indexOf($("layer").value) + 1)]; update(); });
  window.addEventListener("hashchange", fromHash);
  let step = 0;
  function showEvent() {
    const event = bundle.example.trace[step];
    $("event-number").textContent = `${step + 1} / ${bundle.example.trace.length}`;
    $("event-title").textContent = `Event ${event.step}: ${event.action}`;
    $("event-text").textContent = event.action === "write"
      ? `${event.detail.fact.key} = ${event.detail.fact.value}; supplied confidence ${event.detail.fact.confidence}; should retain: ${event.detail.should_retain}. Result: ${event.result.status}.`
      : `Expected: ${event.detail.expected}. Actual answer: ${event.result.answer}. Answer-only check passes.`;
    $("state").textContent = event.after.map((r) => `${r.id}: ${r.key} = ${r.value}`).join("\n") || "Empty";
    $("previous-event").disabled = step === 0;
    $("next-event").disabled = step === bundle.example.trace.length - 1;
  }
  $("previous-event").addEventListener("click", () => { step--; showEvent(); });
  $("next-event").addEventListener("click", () => { step++; showEvent(); });
  $("calibration").replaceChildren(...calibration.map((c) => cells([c.category, c.answer ?? "No answer", c.state_evidence, c.reference_accept ? "Accept" : "Reject", "Pending"])));
  $("frontier").textContent = `Audit quality/context/latency frontier after state and safety screening: ${bundle.audit_frontier.join(", ")}. Local timing can change this frontier on another run.`;
  $("provenance").textContent = `Evidence version: ${bundle.contract.version}. ${bundle.executions} scenario executions. Source hashes are recorded in bundle.json.`;
  fromHash(); showEvent();
} catch (error) {
  $("error").hidden = false;
  $("error").textContent = error.message;
  $("winner").textContent = "Evidence unavailable";
  $("next").disabled = true;
}
