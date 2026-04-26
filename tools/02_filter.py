#!/usr/bin/env python3
"""Split snapshots.tsv into HTML pages, assets to keep, and skipped junk."""
from __future__ import annotations
import re
from pathlib import Path
from urllib.parse import urlsplit, unquote

IN = Path("tools/snapshots.tsv")
OUT_HTML = Path("tools/keep_html.tsv")
OUT_ASSETS = Path("tools/keep_assets.tsv")
OUT_SKIP = Path("tools/skip.tsv")

# Path prefixes that are pure framework chrome — no content
SKIP_PATHS = (
    "/sites/all/modules/",      # Drupal contrib modules CSS/JS
    "/sites/all/themes/",       # Drupal theme CSS/JS
    "/sites/all/libraries/",
    "/modules/",                # Drupal core
    "/misc/",                   # Drupal UI sprites
    "/fs_img/",                 # FreeServers 2001 banner ads
    "/feeds/",                  # Atom comment feeds
    "/user/",                   # User profile pages (mostly empty)
    "/tagadelic",               # Tag-cloud widget pages
    "/tag-cloud",
    "/bookstore/",              # Affiliate Amazon-link pages — not content
)

SKIP_EXACT = {
    "/test",
    "/user",
    "/login",
    "/admin",
}

# Keep these binary types when path passes
KEEP_ASSET_TYPES = (
    "image/jpeg", "image/png", "image/gif", "image/webp", "image/x-icon",
    "image/svg+xml", "application/pdf",
)


def classify(url: str, mime: str) -> tuple[str, str]:
    """Return (bucket, reason). bucket in {html, asset, skip}."""
    parts = urlsplit(url)
    path = parts.path or "/"

    # Drop the atomicrhubarb subdomain — it's a separate side-project, not the recipe site
    if parts.netloc.startswith("atomicrhubarb."):
        return "skip", "subdomain-atomicrhubarb"

    # Wayback short-MIME garbage like "im" / "unk" — try to use extension instead
    if mime in ("im", "unk", ""):
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        ext_to_mime = {
            "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png", "gif": "image/gif",
            "ico": "image/x-icon", "webp": "image/webp", "svg": "image/svg+xml",
            "pdf": "application/pdf",
            "html": "text/html", "htm": "text/html",
            "css": "text/css", "js": "application/javascript",
        }
        mime = ext_to_mime.get(ext, mime)

    # Path-based skip
    for p in SKIP_PATHS:
        if path.startswith(p):
            return "skip", f"path-prefix:{p}"
    if path in SKIP_EXACT:
        return "skip", f"exact:{path}"

    # MIME-based decisions
    if mime == "text/html":
        return "html", "html"
    if mime in KEEP_ASSET_TYPES:
        return "asset", f"asset:{mime}"
    if mime in ("text/css", "application/javascript", "text/javascript",
                "application/atom+xml", "text/x-component", "application/octet-stream"):
        return "skip", f"mime:{mime}"
    if mime == "text/plain":
        return "skip", "mime:text/plain"

    return "skip", f"mime:{mime or 'unknown'}"


def main() -> None:
    rows = [line.rstrip("\n").split("\t") for line in IN.read_text().splitlines() if line.strip()]
    html_rows: list[tuple[str, str, str]] = []
    asset_rows: list[tuple[str, str, str]] = []
    skip_rows: list[tuple[str, str, str, str]] = []

    for ts, url, mime in rows:
        bucket, reason = classify(url, mime)
        if bucket == "html":
            html_rows.append((ts, url, mime))
        elif bucket == "asset":
            asset_rows.append((ts, url, mime))
        else:
            skip_rows.append((ts, url, mime, reason))

    OUT_HTML.write_text("\n".join("\t".join(r) for r in html_rows) + "\n")
    OUT_ASSETS.write_text("\n".join("\t".join(r) for r in asset_rows) + "\n")
    OUT_SKIP.write_text("\n".join("\t".join(r) for r in skip_rows) + "\n")

    print(f"html:    {len(html_rows)}")
    print(f"asset:   {len(asset_rows)}")
    print(f"skip:    {len(skip_rows)}")
    from collections import Counter
    c = Counter(r[3] for r in skip_rows)
    print("\nSkip reasons:")
    for reason, n in c.most_common():
        print(f"  {n:5d}  {reason}")


if __name__ == "__main__":
    main()
