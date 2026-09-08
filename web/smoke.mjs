// Run with Puppeteer installed, against the README HTTP server:
// node web/smoke.mjs http://127.0.0.1:8000/web/
import assert from "node:assert/strict";
import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import puppeteer from "puppeteer";

const url = process.argv[2];
assert(url, "Pass the served web/ URL as the first argument.");
const browser = await puppeteer.launch({
  headless: true,
  ...(process.env.PUPPETEER_EXECUTABLE_PATH
    ? { executablePath: process.env.PUPPETEER_EXECUTABLE_PATH }
    : {}),
});
const screenshots = await mkdtemp(join(tmpdir(), "memory-lab-ui-"));
try {
  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.setViewport({ width: 1440, height: 1100 });
  await page.emulateMediaFeatures([
    { name: "prefers-color-scheme", value: "light" },
  ]);
  await page.goto(url, { waitUntil: "networkidle0" });
  await page.waitForSelector("#explorer:not([hidden])");
  const bundle = await page.evaluate(async () => {
    const root = new URL(
      document.querySelector('meta[name="memory-artifact-base"]').content,
      document.baseURI,
    );
    return (await fetch(new URL("bundle.json", root))).json();
  });
  await page.screenshot({ path: join(screenshots, "desktop.png") });
  await page.emulateMediaFeatures([
    { name: "prefers-color-scheme", value: "dark" },
  ]);
  await page.screenshot({ path: join(screenshots, "desktop-dark.png") });
  await page.emulateMediaFeatures([
    { name: "prefers-color-scheme", value: "light" },
  ]);
  await page.$eval("#comparison", (node) => node.scrollIntoView());
  await page.screenshot({ path: join(screenshots, "comparison.png") });
  await page.click("#all-steps");
  await page.$eval("#trace-section", (node) => node.scrollIntoView());
  await page.screenshot({ path: join(screenshots, "trace.png") });
  const candidates = bundle.candidates.map((candidate) => candidate.id);
  for (const candidate of bundle.candidates) {
    await page.select("#candidate", candidate.id);
    assert.equal(
      await page.$eval("#proposal-title", (node) => node.textContent),
      candidate.label,
    );
    assert.equal(
      new URL(page.url()).searchParams.get("candidate"),
      candidate.id,
    );
    assert(
      (
        await page.$eval("#human-decision", (node) => node.textContent)
      ).includes("Pending human review"),
    );
    for (const scenario of bundle.scenarios) {
      await page.select("#family", scenario.family);
      await page.select("#scenario", scenario.id);
      assert.equal(
        await page.$eval("#evidence-title", (node) => node.textContent),
        scenario.title,
      );
      assert.equal(
        new URL(page.url()).searchParams.get("scenario"),
        scenario.id,
      );
    }
  }
  await page.select("#candidate", candidates[0]);
  const firstUrl = page.url();
  await page.select("#candidate", candidates[1]);
  await page.goBack();
  assert.equal(page.url(), firstUrl);
  assert.equal(
    await page.$eval("#candidate", (node) => node.value),
    candidates[0],
  );
  await page.goForward();
  assert.equal(
    await page.$eval("#candidate", (node) => node.value),
    candidates[1],
  );
  await page.select("#reference", "baseline");
  assert.equal(new URL(page.url()).searchParams.get("reference"), "baseline");
  assert.equal(
    await page.$eval("#metric-reference-label", (node) => node.textContent),
    bundle.candidates[0].label,
  );
  await page.select("#reference", "parent");
  await page.click("#all-steps");
  assert.equal(await page.$eval("#next-step", (node) => node.disabled), true);
  const selectedScenario = await page.$eval("#scenario", (node) => node.value);
  const run = bundle.candidates[1].runs.find(
    (run) => run.scenario_id === selectedScenario,
  );
  assert.equal(
    await page.$$eval("#candidate-trace > li", (nodes) => nodes.length),
    run.trace.length,
  );
  await page.click("#lineage button");
  assert(
    await page.evaluate(
      () => document.activeElement.getAttribute("aria-current") === "true",
    ),
    "Lineage navigation preserves focus",
  );
  assert.equal(
    await page.$eval("#candidate", (node) => node.value),
    candidates[0],
  );
  await page.focus("#candidate");
  await page.keyboard.press("Tab");
  assert.equal(await page.evaluate(() => document.activeElement.id), "family");
  const deepLink = page.url();
  await page.reload({ waitUntil: "networkidle0" });
  assert.equal(page.url(), deepLink);
  await page.goto(`${url}?candidate=missing&scenario=missing&family=missing`, {
    waitUntil: "networkidle0",
  });
  await page.waitForSelector("#explorer:not([hidden])");
  assert(
    candidates.includes(new URL(page.url()).searchParams.get("candidate")),
    "Unknown URL state recovers to a real candidate",
  );
  for (const width of [1440, 768, 390, 320]) {
    await page.setViewport({ width, height: 844 });
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      `Page overflows at ${width}px`,
    );
  }
  await page.setViewport({ width: 390, height: 844 });
  await page.$eval(".controls", (node) => node.scrollIntoView());
  await page.screenshot({ path: join(screenshots, "mobile.png") });
  assert.deepEqual(errors, [], "No browser runtime errors");

  const noJs = await browser.newPage();
  await noJs.setJavaScriptEnabled(false);
  await noJs.goto(url, { waitUntil: "networkidle0" });
  assert.equal(await noJs.$eval("#fallback", (node) => node.hidden), false);
  assert.equal(await noJs.$eval("#loop-nav", (node) => node.hidden), true);
  const report = await (await noJs.$("iframe")).contentFrame();
  assert(
    (await report.$eval("body", (node) => node.textContent)).includes(
      bundle.candidates[0].label,
    ),
  );

  const failed = await browser.newPage();
  await failed.setRequestInterception(true);
  failed.on("request", (request) =>
    request.url().endsWith("bundle.json")
      ? request.abort()
      : request.continue(),
  );
  await failed.goto(url, { waitUntil: "networkidle0" });
  assert.equal(await failed.$eval("#fallback", (node) => node.hidden), false);
  assert(
    (await failed.$eval("#load-message", (node) => node.textContent)).includes(
      "could not load",
    ),
  );
  const malformed = await browser.newPage();
  const broken = structuredClone(bundle);
  broken.candidates.at(-1).runs = [];
  await malformed.setRequestInterception(true);
  malformed.on("request", (request) =>
    request.url().endsWith("bundle.json")
      ? request.respond({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(broken),
        })
      : request.continue(),
  );
  await malformed.goto(url, { waitUntil: "networkidle0" });
  await malformed.waitForSelector("#explorer:not([hidden])");
  await malformed.select("#candidate", broken.candidates.at(-1).id);
  assert.equal(
    await malformed.$eval("#fallback", (node) => node.hidden),
    false,
    "Later selection errors reveal the report fallback",
  );
  assert.equal(
    await malformed.$eval("#explorer", (node) => node.hidden),
    true,
    "Stale evidence is hidden",
  );
  process.stdout.write(
    `PASS: ${bundle.candidates.length} candidates × ${bundle.scenarios.length} scenarios; URL history; trace replay; keyboard; 4 responsive widths; no-JS and load-failure fallbacks.\nScreenshots: ${screenshots}\n`,
  );
} finally {
  await browser.close();
}
