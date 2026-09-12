const $ = (id) => document.getElementById(id);
const root = new URL(
  document.querySelector('meta[name="campaign-artifact-base"]').content,
  document.baseURI,
);
const pct = (v) => `${(v * 100).toFixed(0)}%`;
const pretty = (v) => JSON.stringify(v, null, 2);
const names = {
  evaluated: "Tested",
  iteration_limit: "Iteration limit reached",
  agent_stopped: "Agent stopped",
  provider_error: "Provider error",
  budget_exhausted: "Budget limit",
  usage_unavailable: "Usage unavailable",
  invalid_proposal: "Proposal rejected by validation",
  evaluation_error: "Evaluation error",
};
let experiment,
  renderId = 0;
async function read(path) {
  const response = await fetch(new URL(path, root));
  if (!response.ok)
    throw new Error(`Could not load ${path} (${response.status})`);
  return response.json();
}
function option(value, label) {
  const node = document.createElement("option");
  node.value = value;
  node.textContent = label;
  return node;
}
function link(label, path) {
  const node = document.createElement("a");
  node.textContent = label;
  node.href = new URL(path, root);
  return node;
}
function fail(error) {
  $("loading").hidden = false;
  $("loading").textContent =
    `${error.message}. Use the complete campaign report below, or serve this folder over HTTP.`;
}
async function showIteration() {
  const token = ++renderId;
  const campaign = experiment.campaigns.find(
    (c) => c.id === $("campaign").value,
  );
  const row = campaign.iterations.find(
    (r) => String(r.iteration) === $("iteration").value,
  );
  if (!row) {
    $("iteration-title").textContent =
      "No model call was made in this campaign";
    $("status").textContent = names[campaign.status] ?? campaign.status;
    for (const id of [
      "parent",
      "hypothesis",
      "prediction",
      "patch",
      "outcome",
      "selection",
      "context",
    ])
      $(id).textContent = "";
    $("observations").replaceChildren();
    $("evidence-links").replaceChildren();
    return;
  }
  const query = new URL(location.href);
  query.searchParams.set("campaign", campaign.id);
  query.searchParams.set("iteration", row.iteration);
  history.replaceState(null, "", query);
  const request = await read(`${row.path}/request.json`);
  let proposal = null;
  if (["evaluated", "agent_stopped"].includes(row.status))
    proposal = await read(`${row.path}/proposal.json`);
  if (token !== renderId) return;
  $("iteration-title").textContent =
    `${campaign.id} · iteration ${row.iteration}`;
  $("status").textContent =
    row.status === "evaluated"
      ? "Proposal validated and tested"
      : (names[row.status] ?? row.status);
  $("parent").textContent =
    `Started from ${row.parent_id}. Model: ${row.response_model ?? experiment.model}.`;
  $("observations").replaceChildren(
    ...(proposal?.observations ?? []).map((o) => {
      const li = document.createElement("li");
      li.textContent = `${o.scenario_id}, event ${o.step}: ${o.observation}`;
      return li;
    }),
  );
  $("hypothesis").textContent =
    proposal?.hypothesis ??
    row.reason ??
    row.error_type ??
    "No valid proposal was returned.";
  $("prediction").textContent = proposal?.predicted_effect ?? "Unavailable";
  $("patch").textContent = proposal
    ? pretty(
        Object.fromEntries(
          Object.entries(proposal.patch).filter(([, v]) => v !== null),
        ),
      )
    : "No configuration was applied.";
  $("outcome").textContent = row.feedback
    ? `${pct(row.feedback.metrics.task_success)} of scenarios passed; ${row.feedback.metrics.storage_records.toFixed(2)} stored records per story. ${Object.values(row.feedback.hard_constraints).every((c) => c.passed) ? "All implemented hard checks passed." : "A hard check failed."}`
    : "No new configuration was evaluated.";
  $("selection").textContent =
    row.status === "evaluated"
      ? row.selected_for_next_iteration
        ? "Selected as the next experimental parent. Deployment remains pending human review."
        : "Not selected. The previous parent remains in use; the next request receives this result."
      : "The memory configuration did not change.";
  $("context").textContent = pretty(JSON.parse(request.input));
  const links = [
    link("Request and SGR schema", `${row.path}/request.json`),
    link("Outcome", `${row.path}/result.json`),
  ];
  if (row.response_model)
    links.push(link("Provider response", `${row.path}/response.json`));
  if (row.feedback)
    links.push(
      link(
        "Python evaluation and traces",
        `${row.path}/evaluation/report.html`,
      ),
    );
  $("evidence-links").replaceChildren(...links);
}
function selectCampaign(wanted) {
  const campaign = experiment.campaigns.find(
    (c) => c.id === $("campaign").value,
  );
  $("iteration").replaceChildren(
    ...campaign.iterations.map((r) =>
      option(
        r.iteration,
        `Iteration ${r.iteration} · ${names[r.status] ?? r.status}`,
      ),
    ),
  );
  if (campaign.iterations.some((r) => String(r.iteration) === wanted))
    $("iteration").value = wanted;
  showIteration().catch(fail);
}
async function start() {
  experiment = await read("campaigns.json");
  $("sample").textContent =
    `${experiment.campaigns.length} independent campaigns · up to ${experiment.max_iterations} model decisions each · 20 public test stories per configuration.`;
  $("cost").textContent =
    `Estimated model cost, including cache-write pricing: $${experiment.estimated_cost_usd.toFixed(6)}. Recorded or reserved cost: $${experiment.charged_or_reserved_usd.toFixed(6)}. Budget: $${experiment.budget_usd.toFixed(2)}. Timing and token usage for every call are saved in the evidence.`;
  $("campaign-table").replaceChildren(
    ...experiment.campaigns.map((c) => {
      const tr = document.createElement("tr");
      for (const v of [
        c.id,
        pct(c.baseline.metrics.task_success),
        c.selected ? pct(c.selected.metrics.task_success) : "Unavailable",
        c.iterations.length,
        names[c.status] ?? c.status,
      ]) {
        const td = document.createElement("td");
        td.textContent = v;
        tr.append(td);
      }
      return tr;
    }),
  );
  $("campaign").replaceChildren(
    ...experiment.campaigns.map((c) => option(c.id, c.id)),
  );
  const query = new URL(location.href).searchParams;
  if (experiment.campaigns.some((c) => c.id === query.get("campaign")))
    $("campaign").value = query.get("campaign");
  $("campaign").addEventListener("change", () => selectCampaign());
  $("iteration").addEventListener("change", () => showIteration().catch(fail));
  $("report").href = new URL("report.md", root);
  $("manifest").href = new URL("manifest.json", root);
  $("explorer").hidden = false;
  $("loading").hidden = true;
  selectCampaign(query.get("iteration"));
}
start().catch(fail);
