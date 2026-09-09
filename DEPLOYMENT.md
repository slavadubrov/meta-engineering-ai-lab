# Deploy the static explorer

The Python experiment produces frozen JSON. The browser explorer needs only
HTML, CSS, JavaScript, and those files. No Python hosting, API key, database,
Worker, or live model backend is required. Website deployment is a separate
step from publishing this GitHub repository.

## Build or download a version

Clone the [repository](https://github.com/slavadubrov/closed-loop-ai-lab), then:

```sh
git checkout v0.1.3
uv sync --frozen
uv run --frozen python -m lab verify artifacts/article-01.3 --source
uv run --frozen python -m lab site --output site
uv run --frozen python -m lab serve
```

Open [the packaged explorer](http://127.0.0.1:8000/site/). The exporter refuses
to overwrite an existing output directory; use another output path if `site/`
already exists. To package a fresh experiment, pass its directory with `--release`.

The [v0.1.3 GitHub release](https://github.com/slavadubrov/closed-loop-ai-lab/releases/tag/v0.1.3)
also provides `closed-loop-ai-lab-v0.1.3-site.zip` and `SHA256SUMS`.
The package includes the saved `article-01.3` experiment.
The ZIP contains the **contents** of `site/`, so its root is directly hostable.
Verify the downloaded archive before extracting it:

```sh
shasum -a 256 -c SHA256SUMS
unzip closed-loop-ai-lab-v0.1.3-site.zip -d site
```

## Publish under the existing website

The intended address is:

```text
https://slavadubrov.com/labs/memory-improvement/
```

The deployed layout must be:

```text
/labs/memory-improvement/index.html
/labs/memory-improvement/style.css
/labs/memory-improvement/app.js
/labs/memory-improvement/artifacts/article-01.3/ (complete directory)
```

All paths are relative, so the same package also works at another nested prefix.
Copy the entire package, including the artifact directory. Its generated HTML
report provides the fallback when JavaScript is disabled or evidence cannot load.

For the separate Edge of Context Astro repository:

1. Keep the verified package in a versioned source directory, for example
   `vendor/labs/memory-improvement/v0.1.3/`, with the release URL and archive checksum.
2. Add an explicit build step that copies that version into
   `public/labs/memory-improvement/` **after content import and before Astro builds**.
   In that repository `public/` is generated; do not edit or commit `dist/`.
3. Add a Labs card pointing to `/labs/memory-improvement/`, with repository and
   release links. The article can remain in an unmerged website PR until reviewed. Add its
   public link after publication.
4. Run `make check` and `make build`, then preview the built site. Check a direct
   visit, candidate/scenario links, mobile and keyboard use, browser back, and
   the no-JavaScript report.
5. Publish through the website's existing static deployment workflow, then verify
   the live route and the artifact requests. The Python program does not run on
   the production website.

Astro copies `public/` files into its output without processing them; see the
[Astro project-structure documentation](https://docs.astro.build/en/basics/project-structure/#public).
The package and instructions are ready; the site import step and Labs card are
not installed by this repository. Production or Cloudflare changes still follow
the website's applicable approval policy.

## Preserve the evidence when updating

`article-01.3` contains one run per scenario. Earlier `article-01.1` and
`article-01.2` snapshots remain unchanged.
The original Git metadata points to its staging checkout; file hashes identify
the exact implementation used for each run.

Create a new experiment release and a new Git tag for changed Python, fixtures,
or candidate definitions. Do not replace evidence behind an existing version.
Publication-link fields inside an older bundle describe that snapshot; add
newly available article/release links to the README and explorer instead of
rewriting historical files.

The current interactions explore recorded experiments. Add a live backend only
if a future lab needs to execute new reader-supplied experiments, with that
behavior and its operating budget defined separately.
