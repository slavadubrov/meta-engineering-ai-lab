# Deploy the recorded agent experiment

The browser is static HTML, CSS, JavaScript, and saved JSON. It makes no provider calls and needs no API key. Python generates experiments locally; the deployed site only displays the recorded evidence.

## Export the article study

```sh
git checkout v0.2.1
uv sync --frozen
uv run --frozen python -m lab verify artifacts/agent-study-03 --source
uv run --frozen python -m lab site --output site
python -m http.server 8076 --bind 127.0.0.1 --directory site
```

Open http://127.0.0.1:8076/ and stop with Ctrl-C. The site has two pages:

- `index.html`: the outer LLM agent's campaigns, proposals, feedback, and outcomes.
- `memory.html`: the deterministic memory mechanics and teaching comparisons.

For a different recorded campaign, pass `--campaign-release artifacts/my-agent-study` to `lab site`. Use a new output directory for each export.

The [v0.2.1 release](https://github.com/slavadubrov/closed-loop-ai-lab/releases/tag/v0.2.1) includes `closed-loop-ai-lab-v0.2.1-site.zip` and `SHA256SUMS`. Verify the ZIP with `shasum -a 256 -c SHA256SUMS`, then unzip it into the directory you want to serve. All experiment files are included; the local `.env.local` is not.

## Mount it under an existing website

Copy the exported directory as a unit to a subpath such as `/labs/memory-improvement/`. Keep the relative layout:

```text
/labs/memory-improvement/index.html
/labs/memory-improvement/memory.html
/labs/memory-improvement/campaign.js
/labs/memory-improvement/app.js
/labs/memory-improvement/style.css
/labs/memory-improvement/artifacts/agent-study-03/...
/labs/memory-improvement/artifacts/article-01.6/...
```

For the Notes Astro site, keep a versioned copy of the ZIP output under `vendor/labs/memory-improvement/v0.2.1/`, then copy that directory into `dist/labs/memory-improvement/` after the normal build and discovery steps. A Labs card can link to `/labs/memory-improvement/`; add the article URL to the explorer when the article is public. Verify the entry page, one request JSON, a nested evaluation report, and `memory.html` at the deployed subpath.

This repository does not configure or deploy the production website. Its static output can use the existing static hosting setup; it requires no server functions or usage-based backend.

## Theme behavior

The explorer follows `prefers-color-scheme`. It does not read the Notes site's saved theme selection. The simplest first integration keeps that behavior and links back to the site. To make the theme switch shared later, apply the site's saved light/dark choice before rendering and scope the explorer CSS to its container. Test system-dark/saved-light and system-light/saved-dark combinations before adopting that integration.

The nested generated evaluation report is a separate light page. It has no dependency on the explorer's controls.

## Preserve evidence

Publish a new experiment directory and Git tag when source, prompts, schema, fixtures, or evaluator change. Do not replace files behind a published manifest. The browser export verifies file hashes before packaging and refuses to overwrite an existing output directory.
