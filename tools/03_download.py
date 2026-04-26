#!/usr/bin/env python3
"""Download raw snapshot bodies from web.archive.org.

Uses the `id_` flag in Wayback URLs:  https://web.archive.org/web/<ts>id_/<url>
That gives the original bytes without archive nav injection or link rewriting.

Files land under raw/<host>/<path>, mirroring the source layout. The original
timestamp + source URL are written to a sidecar `<file>.meta.json` so we can
preserve attribution after extraction.

Usage:
  python3 tools/03_download.py raw/             # download HTML
  python3 tools/03_download.py raw/ --assets    # download images
  python3 tools/03_download.py raw/ --all       # both
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urlsplit, unquote


HEADERS = {
    "User-Agent": (
        "rhubarbinfo-archive-rescue/1.0 "
        "(personal preservation; contact maphew@gmail.com)"
    )
}

def old_local_path(out_root: Path, url: str) -> Path:
    """Path that the previous version of safe_local_path would have produced.

    Used only by the fixup pass to migrate already-downloaded files onto the
    new layout. Mirrors the old logic: `/foo` -> `raw/host/foo` (no /index.html).
    """
    p = urlsplit(url)
    host = p.netloc.replace(":80", "").rstrip(".").lower()
    if host == "rhubarbinfo.com":
        host = "www.rhubarbinfo.com"
    path = unquote(p.path)
    if path.endswith("/") or path == "":
        path += "index.html"
    rel = path.lstrip("/").replace(":", "_").replace("?", "_").replace("\\", "_")
    return out_root / host / rel


def safe_local_path(out_root: Path, url: str, mime: str = "") -> Path:
    p = urlsplit(url)
    host = p.netloc.replace(":80", "").rstrip(".").lower()
    if host == "rhubarbinfo.com":
        host = "www.rhubarbinfo.com"
    path = unquote(p.path)
    rel = path.lstrip("/")
    rel = rel.replace(":", "_").replace("?", "_").replace("\\", "_")

    # If this is HTML and the URL has no extension, store as `<path>/index.html`.
    # That way `/recipes` and `/recipes/jam/` can coexist on disk without
    # the bare-name file blocking the directory creation.
    is_html = mime.startswith("text/html") or path.endswith(("/", ".html", ".htm"))
    if path.endswith("/") or path == "":
        rel = (rel + "index.html") if rel.endswith("/") or rel == "" else (rel + "/index.html")
    elif is_html and "." not in rel.rsplit("/", 1)[-1]:
        # No extension on last segment — treat as directory with index.html
        rel = rel + "/index.html"

    return out_root / host / rel


def fetch(ts: str, url: str, dest: Path, retries: int = 4) -> tuple[bool, str]:
    if dest.exists() and dest.stat().st_size > 0:
        return True, "exists"
    wb_url = f"https://web.archive.org/web/{ts}id_/{url}"
    last_err = ""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(wb_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_suffix(dest.suffix + ".part")
            tmp.write_bytes(data)
            tmp.rename(dest)
            meta = dest.with_suffix(dest.suffix + ".meta.json")
            meta.write_text(json.dumps({
                "source_url": url,
                "wayback_timestamp": ts,
                "wayback_url": wb_url,
                "bytes": len(data),
            }, indent=2))
            return True, f"ok({len(data)})"
        except urllib.error.HTTPError as e:
            last_err = f"http{e.code}"
            if e.code in (404, 403, 410):
                return False, last_err
            time.sleep(2 ** attempt)
        except Exception as e:
            last_err = type(e).__name__
            time.sleep(2 ** attempt)
    return False, last_err


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out_root", type=Path)
    ap.add_argument("--html", action="store_true", help="download HTML pages")
    ap.add_argument("--assets", action="store_true", help="download asset files")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=0.5,
                    help="seconds between requests")
    args = ap.parse_args()

    if args.all:
        args.html = args.assets = True
    if not (args.html or args.assets):
        args.html = True

    work: list[tuple[str, str, str]] = []  # (ts, url, kind)
    if args.html:
        for line in Path("tools/keep_html.tsv").read_text().splitlines():
            if line.strip():
                ts, url, _mt = line.split("\t")
                work.append((ts, url, "html"))
    if args.assets:
        for line in Path("tools/keep_assets.tsv").read_text().splitlines():
            if line.strip():
                ts, url, _mt = line.split("\t")
                work.append((ts, url, "asset"))
    if args.limit:
        work = work[:args.limit]

    args.out_root.mkdir(parents=True, exist_ok=True)
    # Fixup: any existing extensionless HTML file that conflicts with new dir
    # layout — move it to <name>/index.html.
    for ts, url, kind in work:
        if kind != "html":
            continue
        old = old_local_path(args.out_root, url)
        new = safe_local_path(args.out_root, url, "text/html")
        if old != new and old.exists() and old.is_file():
            new.parent.mkdir(parents=True, exist_ok=True)
            old.rename(new)
            old_meta = old.with_suffix(old.suffix + ".meta.json")
            if old_meta.exists():
                old_meta.rename(new.with_suffix(new.suffix + ".meta.json"))
    log = (args.out_root / "_download.log").open("a")
    log.write(f"\n=== run @ {time.strftime('%Y-%m-%d %H:%M:%S')} ({len(work)} items) ===\n")

    n_ok = n_skip = n_fail = 0
    for i, (ts, url, kind) in enumerate(work, 1):
        dest = safe_local_path(args.out_root, url, "text/html" if kind == "html" else "")
        ok, msg = fetch(ts, url, dest)
        line = f"{'OK' if ok else 'FAIL'}\t{kind}\t{ts}\t{url}\t{msg}\n"
        log.write(line)
        log.flush()
        if msg == "exists":
            n_skip += 1
        elif ok:
            n_ok += 1
            time.sleep(args.sleep)
        else:
            n_fail += 1
            time.sleep(args.sleep)
        if i % 25 == 0 or i == len(work):
            print(f"[{i}/{len(work)}] ok={n_ok} skip={n_skip} fail={n_fail}", flush=True)
    log.close()

    print(f"\nDone. ok={n_ok} skip={n_skip} fail={n_fail}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
