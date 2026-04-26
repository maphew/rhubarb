#!/usr/bin/env python3
"""Move empty / cruft pages out of the active collections into content/_cleanup/.

Categories detected (see CATEGORY_RULES below):
  photo-stub          drupal photo article whose only content is a dead image + caption
  photo-credit-only   tiny "Photo from someone's photostream" stub with no recipe/article body
  drupal-poll-cruft   Drupal Poll module artifacts (Primary tabs / Dr. Radut / poll vote tables)
  error-page          Wayback-captured 404s and Freeservers "bandwidth exceeded" placeholders
  nav-only            pages that are essentially just the Drupal sidebar navigation
  blogger-month-index Blogger archive month index pages (one TOC link, one image)
  untitled            (untitled) stubs

Files moved are reproducible: rerunning the script is a no-op once they live under _cleanup/.
A TSV manifest is written to content/_cleanup/MANIFEST.tsv recording the original location,
detected category, source URL, Wayback URL, and any broken external image URLs (the lookup
key for hunting the missing photos on other services).

Usage:
    python3 tools/07_cleanup_empty.py            # dry-run, prints plan + manifest preview
    python3 tools/07_cleanup_empty.py --apply    # actually move files
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
CLEANUP = CONTENT / "_cleanup"
COLLECTIONS = ["articles", "recipes", "varieties", "pages", "categories"]

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
EXT_IMG_RE = re.compile(r"!\[[^\]]*\]\((https?://\S+?)(?:\s+\"[^\"]*\")?\)")
LOCAL_IMG_RE = re.compile(r"!\[[^\]]*\]\((/_assets\S+?)(?:\s+\"[^\"]*\")?\)")


def parse(p: Path):
    txt = p.read_text(encoding="utf-8", errors="replace")
    m = FRONTMATTER_RE.match(txt)
    if not m:
        return None
    fm_raw, body = m.group(1), m.group(2)
    fm = {}
    for line in fm_raw.splitlines():
        mm = re.match(r"^([a-zA-Z_][\w]*):\s*(.*)$", line)
        if mm:
            fm[mm.group(1)] = mm.group(2).strip().strip("\"'")
    prose = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", body)
    prose = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", prose)
    prose = re.sub(r"[#>*_`|\-]+", "", prose)
    prose = re.sub(r"\s+", " ", prose).strip()
    ext_imgs = EXT_IMG_RE.findall(body)
    local_imgs = LOCAL_IMG_RE.findall(body)
    return {
        "path": p,
        "fm": fm,
        "body": body,
        "prose": prose,
        "ext_imgs": ext_imgs,
        "local_imgs": local_imgs,
    }


def classify(r: dict) -> str | None:
    fm, body, prose = r["fm"], r["body"], r["prose"]
    title = fm.get("title", "").strip()
    name = r["path"].name

    if title == "(untitled)":
        return "untitled"

    if title.lower() == "page not found":
        return "error-page"
    if "Monthly Bandwidth Exceeded" in title:
        return "error-page"

    # Drupal poll module artifacts
    if "## Primary tabs" in body and "by Dr. Radut" in body:
        return "drupal-poll-cruft"
    if title == "Polls" and "by Dr. Radut" in body:
        return "drupal-poll-cruft"

    # Blogger archive month-index pages: filename pattern + tiny prose
    if re.match(r"the-rhubarb-compendium-\d+\.md$", name) and len(prose) < 50:
        return "blogger-month-index"

    # Drupal sidebar nav with no own content.
    # The nav block can run 5500-10500 chars and the visible link-text alone
    # exceeds the 300-char prose threshold once URLs are stripped, so we don't
    # gate on prose length. Instead we look at structural signals: the body's
    # first non-blank line is `## Navigation`, the body contains the
    # `Table Of Contents` anchor that the Drupal theme always emits, and the
    # vast majority of the body is inside `[...](...)` link syntax.
    body_stripped = body.lstrip()
    if body_stripped.startswith("## Navigation") and "Table Of Contents" in body:
        body_chars = len(body.strip())
        link_chars = sum(len(m.group(0)) for m in re.finditer(r"\[[^\]]*\]\([^)]*\)", body))
        if body_chars > 0 and link_chars / body_chars >= 0.80:
            return "nav-only"

    # Photo-stub: drupal era, near-empty body, references a dead rhubarbinfo.com image
    has_dead_image = any(
        "rhubarbinfo.com" in u and "/files/images/" in u for u in r["ext_imgs"]
    )
    if (
        fm.get("era") == "drupal"
        and len(prose) < 200
        and has_dead_image
        and not r["local_imgs"]
    ):
        return "photo-stub"

    # Photo-credit-only stubs (Flickr/CC photos, no actual content)
    if len(prose) < 250 and re.match(
        r"^\s*Photo from .+photostream", prose, re.IGNORECASE
    ):
        return "photo-credit-only"

    # rhubarb-muffins.md / background-image.md style: tiny "image licensed from istockphoto"
    if len(prose) < 100 and "istockphoto" in body.lower():
        return "photo-stub"

    return None


def annotate_frontmatter(text: str, category: str, collection: str) -> str:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return text
    fm_raw, body = m.group(1), m.group(2)
    extra_lines = []
    if "cleanupReason:" not in fm_raw:
        extra_lines.append(f"cleanupReason: {category}")
    if "originalCollection:" not in fm_raw:
        extra_lines.append(f"originalCollection: {collection}")
    if not extra_lines:
        return text
    return f"---\n{fm_raw}\n" + "\n".join(extra_lines) + f"\n---\n{body}"


def wayback_url(ts: str, src: str) -> str:
    if not ts or not src:
        return ""
    return f"https://web.archive.org/web/{ts}/{src}"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="actually move files")
    args = ap.parse_args()

    plan: list[tuple[str, dict]] = []  # (category, parsed-row)
    for coll in COLLECTIONS:
        d = CONTENT / coll
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.md")):
            r = parse(p)
            if not r:
                continue
            cat = classify(r)
            if cat:
                plan.append((cat, r))

    if not plan:
        print("Nothing to clean up.")
        return

    # Group by category for readable output
    by_cat: dict[str, list[dict]] = {}
    for cat, r in plan:
        by_cat.setdefault(cat, []).append(r)

    print(f"{'(DRY-RUN) ' if not args.apply else ''}Found {len(plan)} files to move:\n")
    for cat in sorted(by_cat):
        rows = by_cat[cat]
        print(f"  [{cat}] {len(rows)} files")
        for r in rows:
            rel = r["path"].relative_to(CONTENT)
            print(f"    {rel}  ({len(r['prose'])} chars prose)")
        print()

    manifest_lines = [
        "category\toriginal_path\ttitle\tsource_url\twayback_url\tbroken_images"
    ]
    for cat, r in plan:
        fm = r["fm"]
        broken = ";".join(
            u for u in r["ext_imgs"]
            if "rhubarbinfo.com" in u and "/files/images/" in u
        )
        manifest_lines.append(
            "\t".join([
                cat,
                str(r["path"].relative_to(CONTENT)),
                fm.get("title", ""),
                fm.get("sourceUrl", ""),
                wayback_url(fm.get("waybackTimestamp", ""), fm.get("sourceUrl", "")),
                broken,
            ])
        )
    manifest_text = "\n".join(manifest_lines) + "\n"

    if not args.apply:
        print("--- MANIFEST.tsv preview (first 10 rows) ---")
        for line in manifest_lines[:11]:
            print(line)
        print("\nRe-run with --apply to perform the move.")
        return

    CLEANUP.mkdir(exist_ok=True)
    for cat, r in plan:
        coll = r["path"].parent.name
        dest_dir = CLEANUP / cat
        dest_dir.mkdir(exist_ok=True)
        # Disambiguate identical basenames coming from different collections
        dest_name = r["path"].name
        if (dest_dir / dest_name).exists():
            dest_name = f"{coll}__{r['path'].name}"
        dest = dest_dir / dest_name

        # Use `git mv` so the rename is tracked in git history. Annotate the
        # frontmatter at the destination after the move.
        subprocess.run(
            ["git", "mv", str(r["path"]), str(dest)],
            cwd=ROOT,
            check=True,
        )
        text = dest.read_text(encoding="utf-8")
        text = annotate_frontmatter(text, cat, coll)
        dest.write_text(text, encoding="utf-8")

    # Append new manifest rows to any existing MANIFEST.tsv rather than
    # clobbering rows from prior cleanup passes.
    manifest_path = CLEANUP / "MANIFEST.tsv"
    new_rows = manifest_lines[1:]  # drop header
    if manifest_path.exists():
        existing = manifest_path.read_text(encoding="utf-8").rstrip("\n").splitlines()
        # Skip any rows whose original_path is already recorded (idempotent).
        recorded = {ln.split("\t", 2)[1] for ln in existing[1:] if "\t" in ln}
        appended = [ln for ln in new_rows if ln.split("\t", 2)[1] not in recorded]
        all_lines = existing + appended
    else:
        all_lines = manifest_lines
    manifest_path.write_text("\n".join(all_lines) + "\n", encoding="utf-8")
    print(f"Moved {len(plan)} files. Manifest at content/_cleanup/MANIFEST.tsv")


if __name__ == "__main__":
    sys.exit(main())
