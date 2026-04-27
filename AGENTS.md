# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project purpose

Archive-rescue rebuild of www.rhubarbinfo.com (Dan Eisenreich, 1994–2024) from
Internet Archive snapshots. Two distinct halves live side-by-side:

1. **Python pipeline** (`tools/`) — one-shot scripts that turn Wayback CDX
   captures into a portable Markdown corpus under `content/`.
2. **Astro static site** (`src/` + `content/`) — renders that corpus to
   `dist/`, deployable to GitHub Pages or Fly.io.

`content/` is the canonical artifact. Astro is just the current renderer; any
SSG could read the same Markdown + frontmatter.

## Commands

```bash
# Site (Astro 5 + npm)
npm install
npm run dev                    # local preview at localhost:4321
npm run build                  # build with site=localhost, base=/
npm run build:ghpages          # SITE=https://maphew.github.io BASE=/rhubarb
npm run build:fly              # SITE=https://rhubarb.fly.dev BASE=/
npm run preview                # serve dist/

# Pipeline (numbered = run order; each step is idempotent)
python3 tools/01_pick_snapshots.py        # CDX enumerate → snapshots.tsv
python3 tools/02_filter.py                # → keep_html.tsv / keep_assets.tsv / skip.tsv
python3 tools/03_download.py raw/ --all   # fetch via Wayback id_ flag (no archive injection)
python3 tools/04_extract.py               # raw HTML → content/<collection>/*.md
python3 tools/05_fetch_external_images.py # Blogger CDN images → public/_assets/
python3 tools/06_rewrite_images.py        # rewrite Markdown image refs to /public/_assets/
python3 tools/07_cleanup_empty.py         # prune empty/parking-page extractions
python3 tools/08_image_recovery.py        # re-scan raw/ for missed image stubs
python3 tools/09_dedup_canonical.py       # dry-run dedup; --apply to actually move files
```

There is no test suite, lint config, or formatter. Verification is by inspection
of `content/_extract.log`, `tools/_dedup_decisions.md`, and `npm run dev`.

## Architecture

### Build/deploy duality (BASE handling)

Site is hosted at two paths: `/rhubarb/` on GH Pages, `/` on Fly. Two pieces
cooperate to make this work:

- `astro.config.mjs` reads `SITE` and `BASE` from env at build time. `BASE`
  is normalized to always have a trailing slash; templates write
  `${import.meta.env.BASE_URL}recipes/`, never a hardcoded path.
- `src/plugins/rewriteAssetUrls.mjs` is a remark plugin that rewrites
  site-absolute `/_assets/foo.jpg` URLs in **Markdown** to prepend the same
  `BASE`. Without it, recipes built for GH Pages would 404 on every image.
  Astro doesn't apply `BASE_URL` to raw Markdown URLs, only to template-side
  `Astro.url`-derived strings — that's why the plugin exists.

When adding new internal links in templates, use `${import.meta.env.BASE_URL}…`.
When adding them in Markdown, write them as `/_assets/…` and let the plugin
prepend `BASE` at build time.

### Content collections

Five collections, all loaded by `glob` from the **repo-root** `content/`
directory (not `src/content/`): `recipes`, `articles`, `varieties`, `pages`,
`categories`. Schema is in `src/content.config.ts` — a single `baseSchema`
shared by all five. Every collection has a corresponding
`src/pages/<collection>/[...slug].astro` that calls `getStaticPaths()` over
`getCollection(...)` and renders through `EntryLayout`.

Frontmatter shape (key fields, all optional except `title`): `era`
(`blogger | drupal | static`), `sourceUrl`, `archivedAt`, `waybackTimestamp`,
`published` (string-or-date, normalized to ISO date), `heroImage`, `tags`.
The `era` field drives the dedup canonical-picking rule below.

### Pipeline architecture

The pipeline is **era-aware**: `04_extract.py` detects whether each captured
HTML page is Blogger (2019–2024), Drupal (2007–2020), or pre-CMS static
(1996–2009), and uses different selectors / kill-lists for each. Output
frontmatter records the era, which downstream tools depend on.

Dedup (`09_dedup_canonical.py`) groups files by `(collection, lowercase(title))`
and picks one canonical per cluster, preferring `blogger > recent drupal >
static`, with image-count and prose-length tiebreakers. Always runs as a
**dry-run** first, writing `tools/_dedup_decisions.md` for human review;
`--apply` then moves losers under `content/_cleanup/duplicates/`. Never run
`--apply` without first reviewing the decision log.

Side-channel artifacts in `tools/` (`*.tsv`, `cdx_*.json`, `_recovery.log`)
are pipeline state, not source-of-truth — the source-of-truth is `raw/`
(gitignored, re-fetchable from Wayback) and `content/` (committed).

## Project conventions

- **Don't edit Markdown in `content/` to fix rendering bugs.** If extraction
  produced wrong output, fix `tools/04_extract.py` and re-run; the corpus is
  meant to be reproducible from `raw/`.
- **Preserve attribution.** Every extracted page carries `sourceUrl` +
  `waybackTimestamp` in frontmatter and they're rendered in the footer of
  `EntryLayout`. Don't strip them.
- **Forum posts, sidebars, Amazon-affiliate bookstore blocks, and the
  `atomicrhubarb.*` subdomain are intentionally out of scope** — see
  README.md "What's preserved, what isn't".
