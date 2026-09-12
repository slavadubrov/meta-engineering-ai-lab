# Export the recorded experiment

The browser displays saved experiment results. It is static HTML, CSS, JavaScript, and JSON, with no provider calls or API key. The article links to the GitHub companion; hosting this explorer is optional.

## Build the portable site

```sh
git clone --branch v0.2.2 --depth 1 https://github.com/slavadubrov/meta-engineering-ai-lab.git
cd meta-engineering-ai-lab
uv sync --frozen
uv run --frozen python scripts/fetch_evidence.py
uv run --frozen python -m lab verify artifacts/agent-study-03 --source
uv run --frozen python -m lab site --output site
python -m http.server 8076 --bind 127.0.0.1 --directory site
```

Download the evidence once. If `artifacts/` already contains it, skip the download and verify it. The exporter refuses to overwrite an existing output directory.

Open http://127.0.0.1:8076/ and stop the server with Ctrl-C. `index.html` follows the agent campaigns; `memory.html` explains the deterministic memory tool. To export your own campaign, pass `--campaign-release artifacts/my-agent-study` to `lab site`.

## Host under a subpath

Copy the complete `site/` directory to your static host. Keep `index.html`, `memory.html`, JavaScript, CSS, and `artifacts/` together. Relative links allow a subpath such as `/labs/memory-improvement/`.

Check both pages and a nested evaluation report after deploying. The explorer follows the browser's light/dark preference. A parent website's theme switch is not shared automatically.

## Preserve the recordings

The [archive descriptor](reports/evidence.json) pins the evidence download by SHA-256. Full records and their original per-file manifests remain unchanged in that archive. Compact reports and selected examples are tracked in `reports/`; all generated and downloaded `artifacts/` are ignored by Git.

If model instructions, fixtures, or evaluation code change, record a new experiment. A documentation or packaging change alone does not require another model run.
