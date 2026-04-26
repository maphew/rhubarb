# Handoff: Rhubarb Compendium cleanup, next 4 tasks

## Context

This is a Wayback-rescue rebuild of `www.rhubarbinfo.com` (Dan Eisenreich, 1994–2024). Repo at `/var/home/matt/dev/rhubarb`, branch `main`. Astro static site rendered from `content/{articles,recipes,varieties,pages,categories}/*.md`. Each `.md` has frontmatter with `era` (`blogger`|`drupal`|`static`), `sourceUrl`, `waybackTimestamp`, `archivedAt`. Pipeline lives in `tools/01_*.py … 06_*.py`; there's now also a `tools/07_cleanup_empty.py`.

**State as of this handoff:** 49 empty/cruft pages were moved out of the active collections into `content/_cleanup/<category>/` (photo-stub, photo-credit-only, drupal-poll-cruft, error-page, blogger-month-index, untitled). Manifest at `content/_cleanup/MANIFEST.tsv`. Each moved file has `cleanupReason:` and `originalCollection:` added to its frontmatter so it can be reinstated. Build is green (`npm run build:ghpages` produces 173 pages, no warnings).

Astro globs `**/*.md` per collection base; anything under `content/_cleanup/` or any other top-level `content/_*/` directory is invisible to the build, so use that as your staging area.

---

## Task 4 — Sweep pure-nav pages (do first; cheap win)

**Goal:** remove pages whose entire content is the Drupal sidebar navigation (table of contents) with no original prose. These aren't "image-recovery candidates," they're Drupal chrome that the extractor misclassified as content.

**Inputs:** Files whose body starts with `## Navigation` and is dominated by sidebar links. Concretely: `content/articles/main.md` (10277 chars, sourceUrl `http://rhubarbinfo.com/image/tid/85` — a Drupal taxonomy/image listing) and `content/recipes/find-by*.md` (`find-by.md`, `find-by-recipe-name.md`, `find-by-ingredient-name.md` + `-2..-14`). ~17 files total.

**Why the existing `tools/07_cleanup_empty.py` didn't catch them:** the heuristic was `prose < 300 chars`, but link-text in the nav (`"Rhubarb History"`, `"Rhubarb Species"`, …) blows past that after URL-stripping.

**Approach:**
1. Add a `nav-only` rule to `tools/07_cleanup_empty.py` that doesn't gate on prose length but on structural signals: body's first non-blank line is `## Navigation`, AND body contains `"Table Of Contents"`, AND link-density is dominant (e.g. ≥80% of non-frontmatter chars are inside `[...](...)`).
2. Re-run dry-run, eyeball the matches, then `--apply`. They'll go to `content/_cleanup/nav-only/` and the manifest will pick them up automatically.
3. `npm run build:ghpages` to confirm no broken intra-site references.

**Success:** `content/articles/main.md` gone, `content/recipes/find-by*` gone, build clean, manifest updated, page count drops to ~156.

---

## Task 1 — Wayback CDX scan to recover the 8 photo-stub images

**Goal:** find surviving snapshots of the dead `http://www.rhubarbinfo.com/files/images/<name>.preview.{png,jpg}` URLs and re-fetch them so the photo-stub articles can be reinstated.

**Inputs:** `content/_cleanup/MANIFEST.tsv`, filter `category == 'photo-stub'`. The `broken_images` column has the exact URL paths to look up:
- `aphids_under_leaf.preview.png`
- `rhubarb_stalks_assorted.preview.jpg`
- `stalks_original.preview.png` (background-image)
- `rhubarb_beetle.preview.png`
- `rhubarb_cherryred_plant.preview.png`
- `rhubarb_frozen.preview.png`
- `goliath_forced.preview.png`
- (rhubarb-muffins.md had no broken-image URL — it was an istockphoto-licensed image with no rhubarbinfo.com asset; this one stays in cleanup)

**Approach:** Write `tools/08_image_recovery.py` modeled on `tools/05_fetch_external_images.py` (already does Wayback `closest`-snapshot lookups). For each broken URL:
1. Hit the [Wayback CDX API](https://web.archive.org/cdx/search/cdx?url=…&output=json) for that URL across 2010–2018 (the Drupal era).
2. Try the most-recent capture first, then fall back through earlier ones; the `?statuscode:200` filter helps skip dead captures.
3. Use the `id_` flag (`https://web.archive.org/web/<ts>id_/<url>`) to fetch raw bytes without Wayback chrome. Existing `tools/05_*` already does this — copy the helper.
4. Save to `public/_assets/<sha>.<ext>` using the same content-hash convention as `06_rewrite_images.py`.
5. For each successful recovery, edit the corresponding file in `content/_cleanup/photo-stub/` to point at the new local asset, drop `cleanupReason`/`originalCollection` from frontmatter, and `git mv` it back into `content/articles/`.
6. Add a `tools/_recovery.log` summarizing hit/miss per URL.

**Success criteria:** ≥3 of 7 photos recovered (realistic — Drupal `/files/images/*.preview.*` was often skipped by Wayback's robots-respecting crawler); recovered articles re-renderable; build green.

**Fallback if CDX hits zero:** check `archive.org/wayback/available?url=…`, then try the `large.png` / non-`.preview` variants of the same filename — the Drupal media filter generated multiple sizes and Wayback may have caught a different one.

---

## Task 2 — Dedup canonical pass

**Goal:** for each duplicate-title cluster, pick one canonical version and move the rest to `content/_cleanup/duplicates/`. Currently ~50 clusters spanning ~80 files (e.g. `forcing-rhubarb{,-2,-3,-4}.md` are four near-identical full-content versions across different `era`s and snapshot dates).

**Inputs:** Run the duplicate-title detector (or look at `content/_duplicates.tsv` for URL-redirect duplicates already known). The first analysis script in this session enumerated all 50 clusters — easy to regenerate.

**Canonical-picking rule (suggested):** within each cluster, prefer in this order:
1. `era == 'blogger'` (latest, cleanest source — blog posts from 2019–2020).
2. `era == 'drupal'` with the **most recent** `archivedAt` (Drupal 2010–2020, image refs more likely to have resolved).
3. `era == 'static'` only if both above are absent (1996–2009 GeoCities-era HTML).

Tiebreakers within an era: file with more `local_imgs` (resolved images) wins over more `ext_imgs` (broken). Then larger `prose` length.

**Approach:**
1. `tools/09_dedup_canonical.py` — parses every file, groups by `(collection, lowercase title)`, applies the rule, writes a per-cluster decision log, then moves losers under `content/_cleanup/duplicates/<canonical-slug>/<filename>.md` (so it's clear what was demoted in favor of which canonical).
2. Update routing: any URL slug that pointed at a now-moved file needs a redirect or to be retargeted. Astro's content collection ID is the filename; check `src/pages/articles/[...slug].astro` and `src/pages/recipes/[...slug].astro` — if `slug` derives from filename, dropping the `-2`/`-3` suffixes won't break since canonical kept the unsuffixed name. **But** if `forcing-rhubarb.md` (blogger) wins over `forcing-rhubarb-2.md` … `-4.md` (drupal/static), the canonical *is* the unsuffixed file, so URLs are fine.
3. Spot-check the decision log before `--apply` — there *are* clusters where the suffixed file has unique value (e.g. `favorite-rhubarb-3.md` was the poll-votes table; that's already in `_cleanup/drupal-poll-cruft/`, but watch for similar patterns elsewhere).
4. `npm run build:ghpages` to confirm no broken refs.

**Success:** content tree halved (~156 → ~85 pages), manifest updated, build green, no broken intra-site links.

---

## Task 3 — Rescue photo-credit-only stubs by inlining into recipes

**Goal:** the 9 files in `content/_cleanup/photo-credit-only/` have **resolved local images** (in `public/_assets/`) plus Flickr/CC attribution, but no recipe text. Their corresponding recipes likely live in `content/recipes/` already without those photos. Splice the photos in.

**Inputs:** `content/_cleanup/photo-credit-only/*.md` — names tell you the target: `strawberry-rhubarb-crisp.md`, `black-bass-with-rhubarb-sauce.md`, `candied-dried-rhubarb.md`, `grilled-chicken-with-rhubarb-sauce.md`, `rhubarb-jam.md`, `rhubarb-on-toasted-banana-bread.md`, `rhubarb-upsidedown-cake.md`, plus `categories/main.md` (this last one is probably a category index — different treatment).

**Approach (per file):**
1. Open the cleanup file, extract the resolved local image path (`/_assets/<hash>.<ext>`) and the attribution markdown (`Photo from X's photostream …`).
2. Locate the matching recipe. Try, in order: `content/recipes/<same-slug>.md`, then partial-match (`grilled-chicken-with-rhubarb-sauce` → `chicken-with-rhubarb.md`), then grep recipes for the dish name. Some won't have a clear home — log those for manual decision.
3. Add `heroImage: /_assets/<hash>.<ext>` to the recipe's frontmatter. Append the attribution as a `## Photo credit` section at the bottom of the recipe.
4. Delete the cleanup stub once spliced.

**Caveats:**
- `categories/main.md` is suspicious — `categories/` is a small collection (7 files) and `main.md` had a similar nav-only smell. Treat separately.
- Don't dedup-merge photos into a recipe that already has a `heroImage`; in that case, just add it inline in the recipe body or skip.
- The "Flickr photostream" links may also be dead — verify they still resolve before propagating attribution. (Wayback fallback: link to `web.archive.org/web/*/{flickr-url}` so credit is preserved even when the source is gone.)

**Success:** all 9 stubs either spliced into their recipe (and removed from `_cleanup/`) or escalated in a `tools/_unmatched.tsv` for manual review. Manifest updated.

---

## Cross-cutting notes for whoever picks this up

- **Re-running `tools/07_cleanup_empty.py` is safe** (idempotent — it skips files already under `content/_cleanup/`).
- **The MANIFEST.tsv must stay in sync** as files come and go. Either re-run the full cleanup script after each pass, or write a small `tools/_regen_manifest.py` that walks `content/_cleanup/*/*.md` and rebuilds the TSV from frontmatter (~20 lines; one was used mid-session, recreate if needed).
- **Commit between tasks.** Each of these is a clean checkpoint. Suggested commit messages:
  - `Sweep pure-nav Drupal sidebar pages into _cleanup/`
  - `Recover N missing photo-stub images from Wayback CDX`
  - `Dedup duplicate-title clusters; pick blogger > drupal > static canonical`
  - `Inline photo-credit stub images into matching recipes`
- **Build check after each pass:** `npm run build:ghpages` (errors are silent unless you grep — `2>&1 | grep -iE "error|warn|fail|missing"`).
- **No frontend route changes needed** for any of these. Slug → file mapping is identity, so file moves under `_cleanup/` just remove pages from the build.
