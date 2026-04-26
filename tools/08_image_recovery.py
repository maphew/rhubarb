#!/usr/bin/env python3
"""Recover the 7 photo-stub images via Wayback CDX + local raw cache fallback.

Strategy per URL:
  1. If `public/_assets/<sha>.<ext>` already exists, skip.
  2. Try Wayback CDX for the exact URL across 2010–2018; iterate captures
     newest-first, fetch via `id_` flag, verify magic-bytes.
  3. Fallback A: try the available-API.
  4. Fallback B: variant filenames (drop `.preview`, swap to `.large`,
     check thumbnail). For each variant, try local `raw/` first, then CDX.
  5. On success, rewrite the stub article to the local asset, drop
     `cleanupReason`/`originalCollection`, git mv to content/articles/.
  6. Update MANIFEST.tsv to drop reinstated rows.
  7. Write tools/_recovery.log (TSV).

Hash convention: sha1(URL)[:16] — matches tools/05_*.py / tools/06_*.py.
The original URL we hash is the one written into the article body
(the .preview.* one) so the mapping in url_map.json wires up cleanly.
"""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "public/_assets"
RAW_IMAGES = ROOT / "raw/www.rhubarbinfo.com/files/images"
URL_MAP = ROOT / "tools/_meta/url_map.json"
RECOVERY_LOG = ROOT / "tools/_recovery.log"
CLEANUP_DIR = ROOT / "content/_cleanup/photo-stub"
ARTICLES_DIR = ROOT / "content/articles"
MANIFEST = ROOT / "content/_cleanup/MANIFEST.tsv"

HEADERS = {
    "User-Agent": (
        "rhubarbinfo-archive-rescue/1.0 (preservation; maphew@gmail.com)"
    )
}

# stub_filename -> (broken_url, [variant_basenames_to_try_as_fallback])
TARGETS = {
    "aphids-under-rhubarb-leaf.md": (
        "http://www.rhubarbinfo.com/files/images/aphids_under_leaf.preview.png",
        ["aphids_under_leaf.png", "aphids_under_leaf.large.png",
         "aphids_under_leaf.thumbnail.png"],
    ),
    "assorted-rhubarb-stalks.md": (
        "http://www.rhubarbinfo.com/files/images/rhubarb_stalks_assorted.preview.jpg",
        ["rhubarb_stalks_assorted.jpg", "rhubarb_stalks_assorted.large.jpg",
         "rhubarb_stalks_assorted.thumbnail.jpg"],
    ),
    "background-image.md": (
        "http://www.rhubarbinfo.com/files/images/stalks_original.preview.png",
        ["stalks_original.png", "stalks_original.large.png",
         "stalks_original.thumbnail.png"],
    ),
    "beetle-on-rhubarb-leaf.md": (
        "http://www.rhubarbinfo.com/files/images/rhubarb_beetle.preview.png",
        ["rhubarb_beetle.png", "rhubarb_beetle.large.png",
         "rhubarb_beetle.thumbnail.png"],
    ),
    "cherryred-rhubarb-plant.md": (
        "http://www.rhubarbinfo.com/files/images/rhubarb_cherryred_plant.preview.png",
        ["rhubarb_cherryred_plant.png", "rhubarb_cherryred_plant.large.png",
         "rhubarb_cherryred_plant.thumbnail.png"],
    ),
    "frozen-rhuarb.md": (
        "http://www.rhubarbinfo.com/files/images/rhubarb_frozen.preview.png",
        ["rhubarb_frozen.png", "rhubarb_frozen.large.png",
         "rhubarb_frozen.thumbnail.png"],
    ),
    "goliath-rhubarb-stalks.md": (
        "http://www.rhubarbinfo.com/files/images/goliath_forced.preview.png",
        ["goliath_forced.png", "goliath_forced.large.png",
         "goliath_forced.thumbnail.png"],
    ),
}

MAGIC = {
    b"\x89PNG\r\n\x1a\n": "png",
    b"\xff\xd8\xff": "jpg",
    b"GIF87a": "gif",
    b"GIF89a": "gif",
    b"RIFF": "webp",  # only if bytes 8..12 == "WEBP" — checked below
}


def detect_image_ext(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
        return "webp"
    return None


def hash_name(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:16]


def http_get(url: str, timeout: int = 60) -> tuple[bytes | None, str]:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(), str(resp.status)
    except urllib.error.HTTPError as e:
        return None, f"http{e.code}"
    except Exception as e:
        return None, type(e).__name__


def cdx_query(url: str) -> list[tuple[str, str]]:
    """Return [(timestamp, original_url)] for status=200 captures, sorted newest-first."""
    api = "https://web.archive.org/cdx/search/cdx?" + urllib.parse.urlencode({
        "url": url,
        "output": "json",
        "filter": "statuscode:200",
        "from": "20100101",
        "to": "20181231",
    })
    data, info = http_get(api, timeout=45)
    if data is None:
        return []
    try:
        rows = json.loads(data)
    except Exception:
        return []
    if not rows or len(rows) < 2:
        return []
    # First row is header: ["urlkey","timestamp","original","mimetype","statuscode","digest","length"]
    header = rows[0]
    ts_idx = header.index("timestamp")
    orig_idx = header.index("original")
    out = [(r[ts_idx], r[orig_idx]) for r in rows[1:]]
    out.sort(key=lambda x: x[0], reverse=True)
    return out


def available_query(url: str) -> str | None:
    api = "https://archive.org/wayback/available?" + urllib.parse.urlencode({"url": url})
    data, _ = http_get(api, timeout=30)
    if data is None:
        return None
    try:
        j = json.loads(data)
    except Exception:
        return None
    snap = j.get("archived_snapshots", {}).get("closest")
    if snap and snap.get("available") and snap.get("status") == "200":
        return snap["timestamp"]
    return None


def try_wayback_for(url: str, polite_delay: float = 1.0) -> bytes | None:
    """Return raw image bytes from Wayback for the URL, or None."""
    captures = cdx_query(url)
    time.sleep(polite_delay)
    if captures:
        # Try up to 4 captures (newest, oldest, plus 2 spread)
        n = len(captures)
        try_idx = sorted(set([0, n - 1, n // 3, (2 * n) // 3]))
        for i in try_idx:
            ts, orig = captures[i]
            wb_url = f"https://web.archive.org/web/{ts}id_/{orig}"
            data, info = http_get(wb_url, timeout=60)
            time.sleep(polite_delay)
            if data and detect_image_ext(data):
                return data
    # available-api fallback
    ts = available_query(url)
    time.sleep(polite_delay)
    if ts:
        wb_url = f"https://web.archive.org/web/{ts}id_/{url}"
        data, info = http_get(wb_url, timeout=60)
        time.sleep(polite_delay)
        if data and detect_image_ext(data):
            return data
    return None


def variant_url(broken_url: str, variant_basename: str) -> str:
    base = broken_url.rsplit("/", 1)[0]
    return f"{base}/{variant_basename}"


def local_raw_for(variant_basename: str) -> Path | None:
    p = RAW_IMAGES / variant_basename
    return p if p.exists() and p.is_file() else None


def recover_one(broken_url: str, variants: list[str], polite_delay: float = 1.0) -> tuple[bytes | None, str, str]:
    """Return (bytes, source_label, ext)."""
    # Step 1: Wayback for the exact preview URL
    print(f"  [1] CDX preview: {broken_url}")
    data = try_wayback_for(broken_url, polite_delay=polite_delay)
    if data:
        return data, f"wayback:{broken_url}", detect_image_ext(data)

    # Step 2: variants — local raw first (zero net cost), then Wayback
    for v in variants:
        local = local_raw_for(v)
        if local:
            blob = local.read_bytes()
            ext = detect_image_ext(blob)
            if ext:
                print(f"  [2] LOCAL raw variant: {v}")
                return blob, f"local-raw:{v}", ext
    for v in variants:
        v_url = variant_url(broken_url, v)
        print(f"  [3] CDX variant: {v}")
        data = try_wayback_for(v_url, polite_delay=polite_delay)
        if data:
            return data, f"wayback:{v_url}", detect_image_ext(data)

    return None, "miss", ""


def update_url_map(broken_url: str, asset_name: str) -> None:
    URL_MAP.parent.mkdir(parents=True, exist_ok=True)
    if URL_MAP.exists():
        m = json.loads(URL_MAP.read_text())
    else:
        m = {}
    m[broken_url] = asset_name
    URL_MAP.write_text(json.dumps(m, indent=2))


def reinstate_article(stub_path: Path, broken_url: str, asset_name: str) -> Path:
    text = stub_path.read_text()
    # Drop cleanupReason / originalCollection lines
    text = re.sub(r"^cleanupReason:.*\n", "", text, flags=re.MULTILINE)
    text = re.sub(r"^originalCollection:.*\n", "", text, flags=re.MULTILINE)
    # Rewrite ALL occurrences of broken_url to local asset path
    text = text.replace(broken_url, f"/_assets/{asset_name}")
    stub_path.write_text(text)

    dest = ARTICLES_DIR / stub_path.name
    subprocess.run(
        ["git", "-C", str(ROOT), "mv", str(stub_path.relative_to(ROOT)), str(dest.relative_to(ROOT))],
        check=True,
    )
    return dest


def update_manifest(reinstated_filenames: set[str]) -> None:
    """Drop rows whose original_path basename is in reinstated_filenames."""
    if not MANIFEST.exists():
        return
    lines = MANIFEST.read_text().splitlines(keepends=True)
    if not lines:
        return
    header = lines[0]
    out = [header]
    drop_count = 0
    for ln in lines[1:]:
        cells = ln.rstrip("\n").split("\t")
        if len(cells) >= 2:
            base = cells[1].rsplit("/", 1)[-1]
            if base in reinstated_filenames:
                drop_count += 1
                continue
        out.append(ln)
    MANIFEST.write_text("".join(out))
    print(f"manifest: dropped {drop_count} reinstated rows")


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    log_lines = ["url\tstatus\tsource\tsha\tdest_path\tnotes\n"]
    reinstated: set[str] = set()
    polite = 1.0

    for stub_name, (broken_url, variants) in TARGETS.items():
        stub_path = CLEANUP_DIR / stub_name
        if not stub_path.exists():
            print(f"SKIP missing stub: {stub_name}")
            continue
        sha = hash_name(broken_url)

        # Idempotency: see if any asset starting with sha already exists.
        existing = list(ASSETS.glob(f"{sha}.*"))
        if existing:
            asset_name = existing[0].name
            print(f"PRE-EXISTING asset for {stub_name}: {asset_name}")
            update_url_map(broken_url, asset_name)
            dest = reinstate_article(stub_path, broken_url, asset_name)
            reinstated.add(stub_name)
            log_lines.append(
                f"{broken_url}\thit-cached\t(asset already present)\t{sha}\t/_assets/{asset_name}\treinstated->{dest.relative_to(ROOT)}\n"
            )
            continue

        print(f"\n=== {stub_name} ===")
        data, source, ext = recover_one(broken_url, variants, polite_delay=polite)
        if data is None:
            print(f"  MISS")
            log_lines.append(f"{broken_url}\tmiss\t-\t{sha}\t-\tleft in _cleanup/\n")
            continue

        asset_name = f"{sha}.{ext}"
        out_path = ASSETS / asset_name
        out_path.write_bytes(data)
        print(f"  HIT ({len(data)} bytes, {ext}) -> {asset_name}  source={source}")
        update_url_map(broken_url, asset_name)
        dest = reinstate_article(stub_path, broken_url, asset_name)
        reinstated.add(stub_name)
        log_lines.append(
            f"{broken_url}\thit\t{source}\t{sha}\t/_assets/{asset_name}\treinstated->{dest.relative_to(ROOT)}\n"
        )

    update_manifest(reinstated)
    RECOVERY_LOG.write_text("".join(log_lines))
    print(f"\nWrote {RECOVERY_LOG.relative_to(ROOT)}")
    print(f"Recovered {len(reinstated)}/{len(TARGETS)} stubs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
