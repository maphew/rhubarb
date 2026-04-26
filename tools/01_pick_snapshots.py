#!/usr/bin/env python3
"""Pick the latest snapshot per URL from a CDX dump (status 200, before cutoff).

Drops forum/cgi/search/admin URLs. Writes:
  - tools/snapshots.tsv  (timestamp\turl\tmimetype  — one row per URL)
  - tools/url_categories.tsv  (path-prefix histogram for sanity check)
"""
from __future__ import annotations
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote

CDX = Path("tools/cdx_full.json")
OUT_SNAPS = Path("tools/snapshots.tsv")
OUT_CATS = Path("tools/url_categories.tsv")

# Skip patterns — forum, dynamic, admin, search, mailto-ish junk
SKIP_RE = re.compile(
    r"(?ix)"
    r"/(forum|forums|phpbb|board|cgi-bin|wp-admin|wp-login|search|"
    r"feed|rss|trackback|comments?/feed)(/|$|\?)"
    r"|/\?(replytocom|share|like|action)="
    r"|\.(php3?|asp|aspx|cgi)(\?|$)"  # most dynamic pages — keep .html, .htm
    r"|/tag/|/author/|/page/\d+"
)

def main() -> None:
    data = json.loads(CDX.read_text())
    header, *rows = data
    # header: ["urlkey","timestamp","original","mimetype","statuscode","digest","length"]
    idx = {k: i for i, k in enumerate(header)}

    # Group by canonical original URL (strip :80, normalize), pick latest timestamp.
    latest: dict[str, tuple[str, str, str]] = {}  # canon_url -> (ts, original, mimetype)
    skipped = Counter()

    for r in rows:
        ts = r[idx["timestamp"]]
        url = r[idx["original"]]
        mt = r[idx["mimetype"]]
        # Normalize
        canon = url.replace(":80/", "/").replace(":80?", "?")
        canon = re.sub(r"^https?://(www\.)?", "https://www.", canon)
        canon = canon.split("#", 1)[0]

        if SKIP_RE.search(canon):
            skipped[skip_label(canon)] += 1
            continue
        # Skip query-stringy crap unless it looks like a useful page
        if "?" in canon and not canon.endswith(".html"):
            # Allow ?p= style permalinks though
            if not re.search(r"\?(p|page_id|cat|recipe)=\w+", canon):
                skipped["query-string"] += 1
                continue

        prev = latest.get(canon)
        if prev is None or ts > prev[0]:
            latest[canon] = (ts, url, mt)

    OUT_SNAPS.write_text(
        "\n".join(f"{ts}\t{url}\t{mt}" for canon, (ts, url, mt) in sorted(latest.items()))
        + "\n"
    )

    # Categorize by first path segment for a sanity overview
    cats = Counter()
    for canon in latest:
        m = re.match(r"https?://[^/]+/([^/?]*)", canon)
        seg = (m.group(1) if m else "") or "(root)"
        # Truncate long filenames to extension class for readability
        if "." in seg and len(seg) > 30:
            seg = "*." + seg.rsplit(".", 1)[-1]
        cats[seg] += 1

    OUT_CATS.write_text(
        "\n".join(f"{n}\t{seg}" for seg, n in cats.most_common()) + "\n"
    )

    print(f"input rows:       {len(rows)}")
    print(f"unique URLs kept: {len(latest)}")
    print(f"skipped:          {sum(skipped.values())}")
    for label, n in skipped.most_common():
        print(f"  - {label:20s} {n}")
    print()
    print("Top path segments:")
    for seg, n in cats.most_common(40):
        print(f"  {n:5d}  {seg}")


def skip_label(url: str) -> str:
    if "/forum" in url.lower() or "phpbb" in url.lower():
        return "forum"
    if "cgi-bin" in url:
        return "cgi-bin"
    if "wp-admin" in url or "wp-login" in url:
        return "wp-admin"
    if ".php" in url:
        return "php"
    if "/tag/" in url or "/author/" in url or re.search(r"/page/\d+", url):
        return "wp-pagination"
    if re.search(r"\.(asp|aspx|cgi)", url):
        return "dynamic"
    return "other"


if __name__ == "__main__":
    main()
