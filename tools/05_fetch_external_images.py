#!/usr/bin/env python3
"""Fetch images referenced from extracted pages via the Wayback Machine.

Many pages embed Blogger CDN images (blogger.googleusercontent.com,
bp.blogspot.com, lh*.googleusercontent.com). Those are not on rhubarbinfo.com
so weren't in our CDX query. We use Wayback's "closest" API to grab the version
nearest to when the page was archived.

Output:
  public/_assets/<sha1>.<ext>             — image bytes
  public/_assets/_url_map.json            — original URL -> local relpath
  public/_assets/_fetch.log               — per-URL fetch log
"""
from __future__ import annotations
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
from collections import defaultdict

ASSETS = Path("public/_assets")
# Note: lives under public/ so Astro serves it as a static file.
RAW = Path("raw")
META = Path("tools/_meta")
URL_MAP = META / "url_map.json"
LOG = META / "fetch.log"

EXT_FROM_MIME = {
    "image/jpeg": "jpg", "image/jpg": "jpg",
    "image/png": "png", "image/gif": "gif",
    "image/webp": "webp", "image/svg+xml": "svg",
    "image/x-icon": "ico", "image/vnd.microsoft.icon": "ico",
}

HEADERS = {
    "User-Agent": (
        "rhubarbinfo-archive-rescue/1.0 (preservation; maphew@gmail.com)"
    )
}

# Match URLs we want to localize (everything except already-local-style refs)
# We localize anything http(s)://... that isn't a wayback link. The Markdown
# may also contain rhubarbinfo.com URLs after extractor rewrote them — those
# should be localized too if we have a copy under raw/.
def is_external_image(url: str) -> bool:
    if not url.startswith(("http://", "https://")):
        return False
    if "web.archive.org" in url:
        return False
    return True


def local_raw_path(url: str) -> Path | None:
    """If `url` corresponds to a file we already downloaded under raw/, return it."""
    p = urllib.parse.urlsplit(url)
    host = p.netloc.replace(":80", "").rstrip(".").lower()
    if host == "rhubarbinfo.com":
        host = "www.rhubarbinfo.com"
    if "rhubarbinfo.com" not in host:
        return None
    rel = urllib.parse.unquote(p.path).lstrip("/")
    rel = rel.replace(":", "_").replace("?", "_").replace("\\", "_")
    candidate = RAW / host / rel
    if candidate.exists() and candidate.is_file():
        return candidate
    return None


def closest_wayback(url: str, target_ts: str) -> str | None:
    """Ask Wayback for the snapshot of `url` closest to `target_ts`."""
    api = "https://archive.org/wayback/available?" + urllib.parse.urlencode({
        "url": url, "timestamp": target_ts,
    })
    try:
        req = urllib.request.Request(api, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            j = json.load(resp)
        snap = j.get("archived_snapshots", {}).get("closest")
        if snap and snap.get("available"):
            ts = snap["timestamp"]
            return f"https://web.archive.org/web/{ts}id_/{url}"
    except Exception:
        return None
    return None


def hash_name(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:16]


def collect_image_urls() -> dict[str, str]:
    """Scan all Markdown files for image refs.

    Returns: {image_url -> reference_archive_ts}
    The ts is taken from the page's frontmatter so we can find a close-in-time
    snapshot of the image on Wayback.
    """
    urls: dict[str, str] = {}
    # Capture only the URL part of ![alt](url "optional title")
    md_re = re.compile(r"!\[[^\]]*\]\((\S+?)(?:\s+\"[^\"]*\")?\s*\)")
    fm_ts_re = re.compile(r"waybackTimestamp:\s*\"?(\d{14})\"?")
    hero_re = re.compile(r'heroImage:\s*"?([^"\n]+)"?')

    for md in Path("content").rglob("*.md"):
        text = md.read_text()
        m = fm_ts_re.search(text)
        page_ts = m.group(1) if m else "20210101000000"
        for u in md_re.findall(text):
            u = u.strip()
            if is_external_image(u):
                if u not in urls or page_ts < urls[u]:
                    urls[u] = page_ts
        # Also pick up heroImage frontmatter (split out of body content)
        h = hero_re.search(text)
        if h:
            u = h.group(1).strip().strip('"')
            if is_external_image(u) and (u not in urls or page_ts < urls[u]):
                urls[u] = page_ts
    return urls


def _fetch_url(url: str, retries: int = 3) -> tuple[bytes | None, str]:
    last = "?"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp:
                ctype = resp.headers.get_content_type() or ""
                data = resp.read()
            if not ctype.startswith("image/"):
                return None, f"not-image:{ctype}"
            return data, ctype
        except urllib.error.HTTPError as e:
            last = f"http{e.code}"
            if e.code in (404, 410):
                return None, last
            time.sleep(2 ** attempt)
        except Exception as e:
            last = type(e).__name__
            time.sleep(2 ** attempt)
    return None, last


def fetch_one(url: str, page_ts: str, retries: int = 3) -> tuple[bytes | None, str]:
    # Try Wayback first (preserves the exact archived bytes)
    wb = closest_wayback(url, page_ts)
    if wb:
        data, info = _fetch_url(wb, retries)
        if data is not None:
            return data, info
    # Fallback: direct fetch from origin. Blogger / Google CDN often still
    # serves images even years later.
    data, info = _fetch_url(url, retries)
    if data is not None:
        return data, info + "+direct"
    return None, "no-snapshot+direct-fail"


def guess_ext(url: str, ctype: str) -> str:
    e = EXT_FROM_MIME.get(ctype)
    if e:
        return e
    m = re.search(r"\.([A-Za-z0-9]{3,4})(?:\?|$)", url)
    if m:
        ext = m.group(1).lower()
        if ext in ("jpg", "jpeg", "png", "gif", "webp", "svg", "ico"):
            return "jpg" if ext == "jpeg" else ext
    return "bin"


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    META.mkdir(parents=True, exist_ok=True)

    existing: dict[str, str] = {}
    if URL_MAP.exists():
        existing = json.loads(URL_MAP.read_text())

    urls = collect_image_urls()
    print(f"unique image URLs referenced: {len(urls)}")
    print(f"already cached:               {sum(1 for u in urls if u in existing)}")

    log = LOG.open("a")
    log.write(f"\n=== run @ {time.strftime('%Y-%m-%d %H:%M:%S')} ({len(urls)} urls) ===\n")
    n_ok = n_skip = n_fail = 0

    items = list(urls.items())
    n_local = 0
    for i, (url, ts) in enumerate(items, 1):
        if url in existing:
            n_skip += 1
            continue
        # If it's a rhubarbinfo.com image we already have on disk, copy it.
        local = local_raw_path(url)
        if local is not None:
            data = local.read_bytes()
            # Guess content-type from extension
            ext = local.suffix.lstrip(".").lower() or "bin"
            if ext == "jpeg":
                ext = "jpg"
            name = f"{hash_name(url)}.{ext}"
            (ASSETS / name).write_bytes(data)
            existing[url] = name
            log.write(f"LOCAL\t{url}\t{name}\t{len(data)}\n")
            n_local += 1
            continue
        data, info = fetch_one(url, ts)
        if data is None:
            log.write(f"FAIL\t{url}\t{info}\n")
            n_fail += 1
            time.sleep(0.4)
            continue
        ext = guess_ext(url, info)
        name = f"{hash_name(url)}.{ext}"
        (ASSETS / name).write_bytes(data)
        existing[url] = name
        log.write(f"OK\t{url}\t{name}\t{len(data)}\n")
        n_ok += 1
        if i % 10 == 0 or i == len(items):
            print(f"[{i}/{len(items)}] ok={n_ok} local={n_local} skip={n_skip} fail={n_fail}", flush=True)
            URL_MAP.write_text(json.dumps(existing, indent=2))
        time.sleep(0.4)

    URL_MAP.write_text(json.dumps(existing, indent=2))
    log.close()
    print(f"\nDone. ok={n_ok} local={n_local} skip={n_skip} fail={n_fail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
