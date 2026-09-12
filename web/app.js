const artifactRoot = new URL(
  document.querySelector('meta[name="memory-artifact-base"]')?.content ??
    "../artifacts/article-01.6/",
  document.baseURI,
);
const $ = (id) => document.getElementById(id);

function showFailure(error) {
  $("load-message").textContent =
    `The interactive evidence could not load. ${error.message} Serve the demo repository over HTTP using the README command, or open the generated report below.`;
  $("explorer").hidden = true;
  $("loop-nav").hidden = true;
  $("fallback").hidden = false;
}

function update(action) {
  try {
    action();
  } catch (error) {
    showFailure(error);
  }
}

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function readable(value) {
  return typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function label(value) {
  return String(value)
    .replaceAll("_", " ")
    .replace(/^./, (letter) => letter.toUpperCase());
}

function dataBlock(value) {
  const pre = element("pre");
  pre.append(element("code", readable(value)));
  return pre;
}

function records(values) {
  const container = element("div");
  if (!values?.length)
    container.append(element("p", "No stored records.", "small muted"));
  for (const record of values ?? []) {
    const card = element("div", undefined, "memory-record");
    const fields = element("details");
    fields.append(element("summary", "All record fields"), dataBlock(record));
    card.append(
      element(
        "strong",
        `${record.entity ?? "Record"} · ${record.key ?? "memory"}`,
      ),
      element("p", readable(record.value)),
      element(
        "p",
        `${record.id} · ${record.tenant} / ${record.user}`,
        "small muted",
      ),
      element(
        "p",
        `Valid from ${record.valid_from} until ${record.valid_to ?? "no end date"}${record.valid_to ? " (end excluded)" : ""}. Source: ${record.source_event_id}.`,
        "small muted",
      ),
      fields,
    );
    container.append(card);
  }
  return container;
}

function eventSummary(event) {
  if (typeof event.detail === "string") return event.detail;
  const detail = event.detail;
  if (event.action === "write")
    return `${detail.fact.entity} · ${detail.fact.key}: ${readable(detail.fact.value)}`;
  if (event.action === "query")
    return `Retrieve ${detail.key} for ${detail.entity}, as of ${detail.as_of}.`;
  if (event.action === "delete")
    return `Delete ${detail.key} for ${detail.entity}.`;
  return "Inspect the recorded inputs and result below.";
}

function metadata(value) {
  const list = element("dl", undefined, "patch");
  for (const [key, item] of Object.entries(value ?? {})) {
    const row = element("div");
    row.append(
      element("dt", label(key)),
      element("dd", item === null ? "Not set" : readable(item)),
    );
    list.append(row);
  }
  return list;
}

function options(select, values, selected) {
  select.replaceChildren(
    ...values.map(([value, text]) => new Option(text, value)),
  );
  select.value = selected;
}

function metric(value, definition = {}) {
  if (value === null || value === undefined) return "Not measured";
  if (typeof value !== "number") return readable(value);
  if (definition.unit === "fraction")
    return new Intl.NumberFormat("en-US", {
      style: "percent",
      maximumFractionDigits: 2,
    }).format(value);
  const formatted = Number.isInteger(value)
    ? value.toLocaleString("en-US")
    : value.toLocaleString("en-US", { maximumFractionDigits: 5 });
  return `${formatted}${definition.unit ? ` ${definition.unit}` : ""}`;
}

async function start() {
  const response = await fetch(new URL("bundle.json", artifactRoot));
  if (!response.ok)
    throw new Error(`Artifact request returned HTTP ${response.status}.`);
  const bundle = await response.json();
  if (
    bundle.schema_version !== "1.0" ||
    !bundle.candidates?.length ||
    !bundle.scenarios?.length
  ) {
    throw new Error(
      "The artifact bundle is missing candidates or scenarios, or uses an unsupported schema.",
    );
  }
  const baseline =
    bundle.candidates.find((candidate) => candidate.id === "baseline") ??
    bundle.candidates.find((candidate) => !candidate.parent_id);
  if (!baseline) throw new Error("The artifact bundle has no baseline.");
  let candidate;
  let scenario;
  let visibleSteps = 1;

  function selectView(fromUrl = false) {
    const query = new URLSearchParams(location.search);
    const defaultCandidate =
      bundle.candidates.find(
        (item) => item.recommendation.status === "recommend_accept",
      ) ?? baseline;
    candidate =
      bundle.candidates.find(
        (item) =>
          item.id === (fromUrl ? query.get("candidate") : $("candidate").value),
      ) ?? defaultCandidate;
    const families = [...new Set(bundle.scenarios.map((item) => item.family))];
    const requestedScenario = fromUrl
      ? (query.get("scenario") ?? "future-move")
      : $("scenario").value;
    const requestedFamily = fromUrl ? query.get("family") : $("family").value;
    const preferredScenario = bundle.scenarios.find(
      (item) => item.id === requestedScenario,
    );
    const firstFailure = bundle.scenarios.find(
      (item) =>
        baseline.runs.some(
          (run) => run.scenario_id === item.id && !run.success,
        ) &&
        candidate.runs.some(
          (run) => run.scenario_id === item.id && run.success,
        ),
    );
    const family = families.includes(requestedFamily)
      ? requestedFamily
      : (preferredScenario ?? firstFailure ?? bundle.scenarios[0]).family;
    const familyScenarios = bundle.scenarios.filter(
      (item) => item.family === family,
    );
    scenario =
      familyScenarios.find((item) => item.id === requestedScenario) ??
      familyScenarios.find((item) => item.id === firstFailure?.id) ??
      familyScenarios[0];
    options(
      $("candidate"),
      bundle.candidates.map((item) => [item.id, item.label]),
      candidate.id,
    );
    options(
      $("family"),
      families.map((item) => [item, label(item)]),
      family,
    );
    options(
      $("scenario"),
      familyScenarios.map((item) => [item.id, item.title]),
      scenario.id,
    );
    const requestedReference = fromUrl
      ? query.get("reference")
      : $("reference").value;
    $("reference").value =
      requestedReference === "baseline" ? "baseline" : "parent";
    visibleSteps = 1;
    render();
    const url = new URL(location.href);
    url.searchParams.set("candidate", candidate.id);
    url.searchParams.set("family", scenario.family);
    url.searchParams.set("scenario", scenario.id);
    url.searchParams.set("reference", $("reference").value);
    if (fromUrl) history.replaceState(null, "", url);
    else if (url.href !== location.href) history.pushState(null, "", url);
  }

  function runFor(item) {
    const run = item.runs.find((run) => run.scenario_id === scenario.id);
    if (!run)
      throw new Error(
        `Missing recorded scenario ${scenario.id} for ${item.id}.`,
      );
    return run;
  }

  function outcome(id, run) {
    $(id).replaceChildren(
      element(
        "span",
        run.success ? "Scenario passes" : "Scenario fails",
        `status ${run.success ? "pass" : "fail"}`,
      ),
      dataBlock(run.actual),
    );
  }

  function render() {
    const selectedRun = runFor(candidate);
    const baselineRun = runFor(baseline);
    const reference =
      $("reference").value === "parent"
        ? (bundle.candidates.find((item) => item.id === candidate.parent_id) ??
          baseline)
        : baseline;
    $("view-status").textContent =
      `${candidate.label} · ${scenario.title} · ${label(scenario.role)} scenario · recorded run ${(selectedRun.repeat ?? 0) + 1}.`;
    $("proposal-title").textContent = candidate.label;
    $("hypothesis").textContent = candidate.hypothesis;
    $("predicted").textContent = candidate.predicted_effect;
    const changes = element("dl", undefined, "patch");
    for (const change of candidate.changes) {
      const row = element("div");
      const value = element("dd");
      value.append(
        element("span", readable(change.before), "change-old"),
        document.createTextNode(" → "),
        element("span", readable(change.after), "change-new"),
      );
      row.append(element("dt", change.field), value);
      changes.append(row);
    }
    $("patch").replaceChildren(
      candidate.changes.length
        ? changes
        : element("p", "Unmodified baseline configuration.", "small muted"),
    );
    $("proposal-meta").replaceChildren(
      element("h3", "Proposer"),
      metadata(candidate.proposer),
      element("h3", "Budget"),
      metadata(candidate.budget),
      element("h3", "Full configuration"),
      dataBlock(candidate.config),
    );
    const lineage = bundle.candidates.map((item) => {
      const button = element(
        "button",
        `${item.parent_id ? "↳ " : ""}${item.label}`,
      );
      button.type = "button";
      button.title = item.parent_id
        ? `Parent: ${item.parent_id}`
        : "Baseline has no parent";
      if (item.id === candidate.id) button.setAttribute("aria-current", "true");
      button.addEventListener("click", () => {
        update(() => {
          $("candidate").value = item.id;
          selectView();
          $("lineage").querySelector('[aria-current="true"]').focus();
        });
      });
      return button;
    });
    $("lineage").replaceChildren(
      element(
        "p",
        `Parent: ${candidate.parent_id ?? "none (baseline)"}`,
        "small muted",
      ),
      ...lineage,
    );
    $("evidence-title").textContent = scenario.title;
    $("scenario-description").textContent = scenario.description;
    $("scenario-meta").replaceChildren(
      element("span", label(scenario.family), "badge"),
      element("span", `${label(scenario.role)} · visible fixture`, "badge"),
    );
    outcome("baseline-outcome", baselineRun);
    outcome("candidate-outcome", selectedRun);
    $("expected").textContent = readable(selectedRun.expected);
    const recommendation = candidate.recommendation;
    const recommendationLabels = {
      retain_baseline: "Retain baseline",
      recommend_accept: "Rule recommendation: accept",
      recommend_reject: "Rule recommendation: reject",
    };
    $("recommendation").replaceChildren(
      element(
        "span",
        recommendationLabels[recommendation.status] ??
          label(recommendation.status),
        `status ${recommendation.status === "recommend_reject" ? "fail" : "pass"}`,
      ),
      element("p", recommendation.rationale),
    );
    $("human-decision").replaceChildren(
      element("strong", label(candidate.decision.status)),
      element("p", candidate.decision.rationale),
      element(
        "p",
        `Reviewer: ${candidate.decision.actor ?? "none recorded"}`,
        "small",
      ),
    );
    $("constraints").replaceChildren(
      ...Object.entries(candidate.summary.hard_constraints).map(
        ([name, result]) => {
          const row = element("div", undefined, "constraint");
          row.append(
            element("span", label(name)),
            element(
              "strong",
              `${result.violations} failed checks out of ${result.checks}`,
              result.passed ? "pass" : "fail",
            ),
          );
          return row;
        },
      ),
    );
    $("sample-size").textContent =
      `${candidate.summary.task_count} distinct scenarios · ${candidate.summary.repeat_count} ${candidate.summary.repeat_count === 1 ? "run" : "runs"} per scenario`;
    $("metric-candidate-label").textContent = candidate.label;
    $("metric-reference-label").textContent = reference.label;
    $("metrics").replaceChildren(
      ...Object.entries(candidate.summary.metrics)
        .filter(
          ([key]) =>
            key !== "success_repeat_stddev" ||
            candidate.summary.repeat_count > 1,
        )
        .map(([key, value]) => {
          const definition = bundle.metric_definitions[key] ?? {
            label: label(key),
          };
          const row = element("tr");
          const name = element("th", definition.label);
          name.scope = "row";
          row.append(
            name,
            element(
              "td",
              metric(reference.summary.metrics[key], definition),
              "metric-value",
            ),
            element("td", metric(value, definition), "metric-value"),
            element(
              "td",
              definition.description ??
                "See the artifact for this metric's definition.",
              "metric-description",
            ),
          );
          return row;
        }),
    );
    $("uncertainty").replaceChildren(
      element(
        "p",
        "Paired comparison against the named parent, as exported by Python. All fixtures were visible during authorship; evaluation roles are diagnostic partitions, not a blind holdout.",
        "small muted",
      ),
      metadata(candidate.summary.paired),
      element("h3", "Metrics by fixture role"),
      dataBlock(candidate.summary.role_metrics),
    );
    $("state-before").replaceChildren(records(selectedRun.before));
    $("state-after").replaceChildren(records(selectedRun.after));
    const diff = selectedRun.state_diff;
    $("state-diff").replaceChildren(
      ...Object.entries(diff).map(([kind, values]) => {
        const group = element("div", undefined, "diff-group");
        group.append(element("h4", `${label(kind)} · ${values.length}`));
        if (!values.length) group.append(element("p", "None.", "small muted"));
        else
          group.append(
            kind === "changed" ? dataBlock(values) : records(values),
          );
        return group;
      }),
    );
    renderTrace();
  }

  function renderTrace() {
    const beforeRun = runFor(baseline);
    const afterRun = runFor(candidate);
    const total = Math.max(beforeRun.trace.length, afterRun.trace.length);
    visibleSteps = Math.min(visibleSteps, total);
    $("step-status").textContent =
      `Showing ${visibleSteps} of ${total} recorded steps`;
    $("previous-step").disabled = visibleSteps <= 1;
    $("next-step").disabled = visibleSteps >= total;
    $("all-steps").disabled = visibleSteps >= total;
    $("candidate-trace-title").textContent = `${candidate.label} trace`;
    for (const [id, run] of [
      ["baseline-trace", beforeRun],
      ["candidate-trace", afterRun],
    ]) {
      $(id).replaceChildren(
        ...run.trace.slice(0, visibleSteps).map((event) => {
          const item = element("li");
          item.append(
            element("h4", `${event.step}. ${label(event.action)}`),
            element("p", eventSummary(event)),
          );
          if (event.result?.status)
            item.append(
              element(
                "p",
                `${label(event.result.status)}${event.result.reason ? ` · ${label(event.result.reason)}` : ""}`,
                "small muted",
              ),
            );
          if (event.answer !== undefined)
            item.append(
              element("p", "Recorded answer", "small muted"),
              dataBlock(event.answer),
            );
          const inspect = element("details");
          inspect.append(
            element("summary", "Inspect stored state & retrieval"),
            element("h4", "Recorded inputs"),
            dataBlock(event.detail),
          );
          if (event.result)
            inspect.append(
              element("h4", "Recorded result"),
              dataBlock(event.result),
            );
          if (event.retrieved_ids?.length) {
            inspect.append(
              element("h4", "Retrieved memory IDs"),
              dataBlock(event.retrieved_ids),
            );
            const retrieved = event.retrieved_ids
              .map((id) =>
                [...event.before, ...event.after].find(
                  (record) => record.id === id,
                ),
              )
              .filter(Boolean);
            inspect.append(
              records(retrieved),
              element("h4", "Packed into context"),
              dataBlock(event.packed_ids ?? []),
            );
          } else
            inspect.append(
              element(
                "p",
                "No memories retrieved at this step.",
                "small muted",
              ),
            );
          inspect.append(
            element("h4", "State before"),
            records(event.before),
            element("h4", "State after"),
            records(event.after),
          );
          if (event.state_diff)
            inspect.append(
              element("h4", "Structured change at this step"),
              dataBlock(event.state_diff),
            );
          item.append(inspect);
          return item;
        }),
      );
    }
  }

  $("limitations").replaceChildren(
    ...[...bundle.disclosures, ...bundle.limitations].map((text) =>
      element("li", text),
    ),
  );
  $("blocked-proposals").replaceChildren(
    ...bundle.blocked_proposals.map((proposal) => {
      const item = element("div");
      item.append(
        element("h3", proposal.id),
        element("p", proposal.error),
        dataBlock(proposal.patch),
      );
      return item;
    }),
  );
  $("reproduction-command").textContent = bundle.reproduction_command;
  const links = [
    ["Frozen HTML report", "report.html"],
    ["Markdown report", "report.md"],
    ["Manifest & content hashes", "manifest.json"],
    ["Download explorer JSON", "bundle.json"],
    ["All recorded runs", "runs.jsonl"],
  ].map(([text, path]) => {
    const link = element("a", text);
    link.href = new URL(path, artifactRoot).href;
    if (path.endsWith("json") || path.endsWith("jsonl")) link.download = path;
    return link;
  });
  for (const [name, destination] of Object.entries(bundle.links)) {
    if (!destination) continue;
    const url = new URL(destination, location.href);
    if (!["http:", "https:"].includes(url.protocol)) continue;
    const link = element("a", label(name));
    link.href = url.href;
    links.push(link);
  }
  $("artifact-links").replaceChildren(...links);
  $("provenance").replaceChildren(
    metadata({
      release_id: bundle.release_id,
      generated_at: bundle.generated_at,
      schema_version: bundle.schema_version,
      ...bundle.provenance,
    }),
  );
  for (const id of ["candidate", "family", "scenario", "reference"])
    $(id).addEventListener("change", () => update(() => selectView()));
  $("previous-step").addEventListener("click", () => {
    visibleSteps -= 1;
    update(renderTrace);
  });
  $("next-step").addEventListener("click", () => {
    visibleSteps += 1;
    update(renderTrace);
  });
  $("all-steps").addEventListener("click", () => {
    visibleSteps = Infinity;
    update(renderTrace);
  });
  $("share").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(location.href);
      $("view-status").textContent =
        "Link copied. It preserves the candidate, task family, scenario, and comparison reference.";
    } catch {
      $("view-status").textContent =
        "Copy the URL from your browser's address bar. It already preserves this view.";
    }
  });
  window.addEventListener("popstate", () => update(() => selectView(true)));
  selectView(true);
  $("explorer").hidden = false;
  $("loop-nav").hidden = false;
  $("fallback").hidden = true;
}

start().catch(showFailure);
