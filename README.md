# The Rhubarb Compendium — archive rescue

A non-commercial preservation rebuild of [www.rhubarbinfo.com][orig], whose
domain went dark on 2024-10-23 and is now a casino redirect. Every page
here is a clean re-render of an [Internet Archive][wb] snapshot.

[orig]: https://web.archive.org/web/2024*/rhubarbinfo.com
[wb]: https://web.archive.org/

## Layout

| Path | Purpose |
| --- | --- |
| `tools/` | Python pipeline: enumerate → filter → download → extract → fetch images → rewrite |
| `raw/` | Raw HTML/asset bytes downloaded from Wayback (gitignored) |
| `content/` | Extracted Markdown + frontmatter, organized by collection (canonical corpus) |
| `public/_assets/` | Re-fetched external images (Blogger CDN) — served as Astro static files |
| `src/` | Astro site (layouts, pages, content config) |

The `content/` tree is the canonical preserved corpus: portable, future-proof,
re-renderable with any static-site generator. Astro is just the current renderer.

## Rebuilding the corpus from scratch

```bash
# 1. enumerate every captured URL via Wayback CDX API
python3 tools/01_pick_snapshots.py
# 2. split into HTML / asset / skip buckets
python3 tools/02_filter.py
# 3. download raw bytes via Wayback id_ flag (no archive injection)
python3 tools/03_download.py raw/ --all
# 4. parse HTML → Markdown + frontmatter (era-aware: blogger/drupal/static)
python3 tools/04_extract.py
# 5. fetch off-site images (Blogger CDN) via Wayback closest-snapshot
python3 tools/05_fetch_external_images.py
# 6. rewrite Markdown image refs to point at /public/_assets/
python3 tools/06_rewrite_images.py
```

## Building & deploying

```bash
npm install
npm run dev                    # local preview
npm run build:ghpages          # build for https://maphew.github.io/rhubarb/
npm run build:fly              # build for https://rhubarb.fly.dev/
```

GitHub Pages deploys via `.github/workflows/deploy.yml` on push to `main`.

For Fly.io, serve `dist/` with any static container (`flyctl launch` with
nginx/caddy works fine).

## What's preserved, what isn't

**Preserved:**

- Recipes, articles, growing guides, varieties pages, taxonomy listings.
- Hero images and inline photography (Blogger CDN, re-hosted locally).
- Original URLs and archive timestamps on every page (attribution).

**Skipped:**

- Forum posts (per project scope).
- Drupal/Blogger UI chrome (sidebars, navigation, ads).
- Amazon-affiliate bookstore link blocks (the books still exist; the affiliate
  IDs are dead).
- The `atomicrhubarb.rhubarbinfo.com` subdomain (separate side-project, not
  part of the Compendium).

## Attribution

All credit for the original content belongs to the original author(s) of
www.rhubarbinfo.com. This rescue effort exists to keep the work findable.
If you are the original author and would like attribution updated or content
removed, please open an issue.

## License

Pipeline code (`tools/`, `src/`) is released under the repository's `LICENSE`.
The preserved content under `content/` retains its original copyright (whatever
that may be) and is re-published here under the principle that allowing a
deeply-loved community resource to vanish into a casino-domain squat is the
worse outcome.
