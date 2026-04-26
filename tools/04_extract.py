#!/usr/bin/env python3
"""Extract HTML pages into Markdown + frontmatter under content/.

Three eras handled:
  - Blogger (2019-2024): generator=blogger, content in .post-body / .entry-content
  - Drupal  (2007-2020): generator=Drupal, content in .field-name-body
  - Static  (2000-2006): pre-CMS, content in <body>

Outputs:
  content/<collection>/<slug>.md   — frontmatter + Markdown body
  content/_extract.log             — per-file extraction notes
  content/_external_images.tsv     — external images referenced (for later fetch)
"""
from __future__ import annotations
import json
import re
import sys
import urllib.parse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

from bs4 import BeautifulSoup, Tag
from markdownify import markdownify

RAW = Path("raw")
OUT = Path("content")
LOG = OUT / "_extract.log"
EXT_IMG_LOG = OUT / "_external_images.tsv"
DUPS = OUT / "_duplicates.tsv"

# Wayback nav strips inserted into raw HTML — we used id_ flag, so should be clean,
# but be defensive anyway.
WAYBACK_RE = re.compile(r"^https?://web\.archive\.org/web/\d+([a-z_]*)/")

# Strip these elements from extracted body (Blogger UI / Drupal blocks)
KILL_SELECTORS = [
    "script", "style", "noscript", "iframe", "form",
    ".post-footer", ".comments", ".post-share-buttons",
    ".jump-link", ".feed-links", ".navigation", ".blog-pager",
    ".sidebar", "#sidebar", ".region-sidebar-first", ".region-sidebar-second",
    ".region-header", ".region-footer", "#header", "#footer",
    ".breadcrumb", "#breadcrumb",
    ".node-readmore", ".links",
    "[class*='AdSense']", "[id*='AdSense']",
    "[class*='banner-ad']",
]

# Page-not-found / parking-page detection
PARKING_PHRASES = (
    "this page has moved",
    "click here for the new home page",
    "freeservers",  # FreeServers/Tripod 2001 redirect pages
    "not currently available",
    "you have reached an obsolete page",
)

# Source-URL patterns to skip entirely (irrelevant to the rescued corpus).
# /bookstore/* are 2001-era Amazon affiliate pages — pure affiliate noise.
SKIP_URL_RE = re.compile(r"/bookstore/", re.I)

# SEO spam injected into compromised Drupal nodes around 2010-2012.
# Wayback captured the spam, so we filter at extraction time.
SPAM_TITLE_RE = re.compile(
    r"(?i)\b("
    r"louis vuitton|hermes (?:birkin|outlet|bags?)|mulberry (?:bags?|handbags?|hobo|mitzy|uk)|"
    r"nike (?:air max|air jordan|nfl|mercurial|free run)|air jordan|nike-air-(?:max|jordan)|"
    r"oakley sunglasses|polo (?:shirts?|outlet|ralph lauren)|ralph lauren|"
    r"rolex (?:daytona|replica)|replica watch(?:es)?|chopard replica|iwc replica|"
    r"hostgator|wordpress hosting|magento (?:web )?hosting|amazon web hosting|"
    r"windows vps|vps hosting|web hosting (?:provider|coupons?)|"
    r"nfl jerseys?|mlb jerseys?|throwback jerseys?|"
    r"wedding (?:dress(?:es)?|gowns?)|empire waist wedding|mermaid wedding|bridal gowns?|"
    r"ugg boots?|supra (?:skate )?shoes?|coach outlet|beats by dre|"
    r"longchamp|cafepress|"
    r"office 2007|office 2010|microsoft office|"
    r"chicharito|whc addicted|liposuction|"
    r"discount (?:wedding|polo)|cheap (?:polo|football|rolex|nike|nfl|ralph lauren)|"
    r"sac longchamp|ck underwear|football boots|"
    r"birkin bag|hermes outlet"
    r")\b"
)

# Drupal-style slugs for spam pages: "louis-vuitton-m56889-jvughw" etc.
SPAM_SLUG_RE = re.compile(
    r"(?i)\b("
    r"louis-vuitton|hermes|mulberry|oakley|ralph-lauren|rolex|replica|"
    r"hostgator|nike-air-(?:max|jordan)|nike-nfl|nike-mercurial|air-jordan|"
    r"wedding-dress(?:es)?|wedding-gowns?|bridal-gowns?|"
    r"ugg-boots?|coach-outlet|beats-by-dre|polo-shirts?|"
    r"sac-longchamp|ck-underwear|liposuction|chicharito|whc-addicted|"
    r"throwback-jerseys?|nfl-jerseys?|mlb-jerseys?"
    r")\b"
)


def looks_like_spam(title: str, slug: str, body_text: str) -> bool:
    """Detect SEO spam injected into compromised Drupal nodes."""
    if SPAM_TITLE_RE.search(title) or SPAM_SLUG_RE.search(slug):
        return True
    bt = body_text.lower()
    rhubarb_hits = bt.count("rhubarb")
    # The site is literally The Rhubarb Compendium — any non-trivial body that
    # never says "rhubarb" once is a hijacked node.
    if rhubarb_hits == 0 and len(bt) > 200:
        return True
    spam_hits = len(SPAM_TITLE_RE.findall(bt))
    if rhubarb_hits < 2 and spam_hits >= 3:
        return True
    return False


@dataclass
class Extracted:
    title: str
    body_md: str
    era: str
    collection: str
    slug: str
    source_url: str
    archived_ts: str
    archived_iso: str
    publish_date: str | None
    hero_image: str | None
    description: str | None
    external_images: list[str]
    notes: list[str]


def detect_era(soup: BeautifulSoup) -> str:
    gen = soup.find("meta", attrs={"name": "generator"}) or soup.find("meta", attrs={"name": "Generator"})
    g = (gen.get("content", "").lower() if gen else "")
    if "blogger" in g:
        return "blogger"
    if "drupal" in g:
        return "drupal"
    # Drupal sometimes lacks the generator on cached pages — check for shortlink to /node/
    if soup.find("link", rel="shortlink", href=re.compile(r"/node/\d+")):
        return "drupal"
    if soup.select_one(".field-name-body, .node-content, .region-content"):
        return "drupal"
    return "static"


def pick_body(soup: BeautifulSoup, era: str) -> Tag | None:
    if era == "blogger":
        for sel in [".post-body", ".entry-content", ".post"]:
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                return el
    if era == "drupal":
        for sel in [".field-name-body", ".node-content .content",
                    ".node-content", "#content-area", "#main-content #content",
                    "#content"]:
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                return el
    # Static fallback
    body = soup.body
    return body


def clean_body(el: Tag, base_url: str) -> tuple[Tag, list[str]]:
    """Remove junk in-place, return list of external image URLs referenced."""
    for sel in KILL_SELECTORS:
        for x in el.select(sel):
            x.decompose()
    # Drop wayback timetravel / archive injection if any survived
    for x in el.select("[id^='wm-']"):
        x.decompose()
    # Resolve relative URLs against canonical source URL
    ext_imgs: list[str] = []
    for tag, attr in [("a", "href"), ("img", "src"), ("img", "data-src"), ("source", "src")]:
        for t in el.find_all(tag):
            v = t.get(attr)
            if not v:
                continue
            v = WAYBACK_RE.sub("", v)
            v = urllib.parse.urljoin(base_url, v)
            t[attr] = v
            if tag in ("img", "source"):
                ext_imgs.append(v)
    return el, ext_imgs


def title_from(soup: BeautifulSoup, era: str) -> str:
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return og["content"].strip()
    if era == "blogger":
        h = soup.select_one(".post-title, h3.post-title")
        if h:
            return h.get_text(strip=True)
    if era == "drupal":
        h = soup.select_one("#page-title, h1.title, h1#page-title")
        if h:
            return h.get_text(strip=True)
    if soup.title:
        t = soup.title.get_text(strip=True)
        # strip site-name suffix
        for sep in [" | ", " - ", ": "]:
            if sep in t:
                # Heuristic: site name usually shorter
                left, right = t.split(sep, 1)
                if "rhubarb" in left.lower() and "rhubarb" not in right.lower():
                    return right
                if "rhubarb" in right.lower() and "rhubarb" not in left.lower():
                    return left
        return t
    return "(untitled)"


def slugify(s: str, fallback: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    s = s[:80] or re.sub(r"[^a-z0-9]+", "-", fallback.lower()).strip("-")
    return s or "untitled"


def collection_for(url: str, era: str, body_text: str) -> str:
    p = urllib.parse.urlsplit(url).path
    if re.search(r"/recipe(?:s)?/", p):
        return "recipes"
    if re.search(r"/varieties?(?:/|$)", p):
        return "varieties"
    if re.search(r"/taxonomy/term/", p):
        return "categories"
    # Blogger paths look like /YYYY/MM/slug.html
    if era == "blogger" and re.match(r"/\d{4}/\d{2}/[^/]+\.html$", p):
        # Decide by content hint
        bt = body_text.lower()
        if any(w in bt for w in ["preheat", "ingredients", "tablespoon", "teaspoon", "1 cup", "stir in", "bake at"]):
            return "recipes"
        return "articles"
    if p in ("/", "/home", "/index.html"):
        return "pages"
    # Drupal nodes — need body content to decide
    bt = body_text.lower()
    if any(w in bt for w in ["preheat", "ingredients:", "1 cup ", "tablespoon", "stir in"]):
        return "recipes"
    return "articles"


def parse_blogger_date(soup: BeautifulSoup) -> str | None:
    # Blogger templates often have <h2 class='date-header'><span>Date</span></h2>
    el = soup.select_one(".date-header span, .published, abbr.published, time")
    if el:
        v = el.get("datetime") or el.get("title") or el.get_text(strip=True)
        if v:
            return v
    return None


def to_iso_date(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    # ISO-ish already
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    # "Saturday, March 30, 2019"
    for fmt in ("%A, %B %d, %Y", "%B %d, %Y", "%d %B %Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def looks_like_parking(text: str) -> bool:
    t = text.lower()
    if len(t) < 200 and any(p in t for p in PARKING_PHRASES):
        return True
    return False


def extract_one(html_path: Path, meta: dict) -> Extracted | None:
    base = meta["source_url"]
    if SKIP_URL_RE.search(base):
        return None
    raw = html_path.read_text(errors="replace")
    soup = BeautifulSoup(raw, "html.parser")
    era = detect_era(soup)

    body_el = pick_body(soup, era)
    if body_el is None:
        return None
    # Get plain text first to detect parking pages
    txt = body_el.get_text(" ", strip=True)
    if looks_like_parking(txt):
        return None

    body_el, ext_imgs = clean_body(body_el, base)

    # Convert to Markdown
    md = markdownify(str(body_el), heading_style="ATX", bullets="-", strip=["span", "font"])
    # Unwrap Blogger lightbox links: [![](thumb)](full) -> ![](full)
    md = re.sub(
        r"\[!\[\]\(([^)]+)\)\]\(([^)]+)\)",
        lambda m: f"![]({m.group(2)})",
        md,
    )
    # Collapse 3+ blank lines
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    if not md or len(md) < 30:
        return None

    title = title_from(soup, era)
    coll_slug_preview = urllib.parse.urlsplit(base).path.strip("/").replace("/", "-")
    if looks_like_spam(title, coll_slug_preview, txt):
        return None
    description = (soup.find("meta", property="og:description") or {}).get("content", "") if soup.find("meta", property="og:description") else ""
    hero = (soup.find("meta", property="og:image") or {}).get("content", "") if soup.find("meta", property="og:image") else ""
    pub_date = parse_blogger_date(soup) if era == "blogger" else None

    coll = collection_for(base, era, txt)
    slug = slugify(
        title,
        urllib.parse.urlsplit(base).path.strip("/").replace("/", "-").rsplit(".html", 1)[0],
    )

    ts = meta["wayback_timestamp"]
    iso = (
        f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}T{ts[8:10]}:{ts[10:12]}:{ts[12:14]}Z"
        if len(ts) >= 14 else ""
    )

    return Extracted(
        title=title,
        body_md=md,
        era=era,
        collection=coll,
        slug=slug,
        source_url=base,
        archived_ts=ts,
        archived_iso=iso,
        publish_date=pub_date,
        hero_image=hero or None,
        description=(description or None),
        external_images=ext_imgs,
        notes=[],
    )


def yaml_escape(s: str) -> str:
    if s is None:
        return '""'
    s = str(s)
    needs_quote = (
        any(c in s for c in ":#\"'\n[]{},&*?|<>=!%`@\\")
        or s.strip() != s
        or not s
        or s.lstrip("-").replace(".", "", 1).isdigit()  # purely numeric
        or s.lower() in ("true", "false", "null", "yes", "no", "on", "off")
    )
    if needs_quote:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def write_extracted(ex: Extracted, used_slugs: dict[tuple[str, str], int]) -> Path:
    key = (ex.collection, ex.slug)
    n = used_slugs.get(key, 0)
    used_slugs[key] = n + 1
    slug = ex.slug if n == 0 else f"{ex.slug}-{n+1}"

    out = OUT / ex.collection / f"{slug}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    fm = ["---"]
    fm.append(f"title: {yaml_escape(ex.title)}")
    if ex.description:
        fm.append(f"description: {yaml_escape(ex.description)}")
    fm.append(f"era: {ex.era}")
    fm.append(f"collection: {ex.collection}")
    fm.append(f"sourceUrl: {yaml_escape(ex.source_url)}")
    fm.append(f"archivedAt: {yaml_escape(ex.archived_iso)}")
    fm.append(f"waybackTimestamp: {yaml_escape(ex.archived_ts)}")
    if ex.publish_date:
        iso = to_iso_date(ex.publish_date)
        if iso:
            fm.append(f"published: {iso}")
        else:
            fm.append(f"publishedRaw: {yaml_escape(ex.publish_date)}")
    if ex.hero_image:
        fm.append(f"heroImage: {yaml_escape(ex.hero_image)}")
    fm.append("---")
    out.write_text("\n".join(fm) + "\n\n" + ex.body_md + "\n")
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    log = LOG.open("w")
    ext_log = EXT_IMG_LOG.open("w")
    dup_log = DUPS.open("w")

    used_slugs: dict[tuple[str, str], int] = {}
    counters: Counter[str] = Counter()
    seen_digests: dict[str, str] = {}  # md hash -> first source URL (dedupe by content)

    html_files = sorted(RAW.rglob("*.html"))
    for h in html_files:
        if h.name.endswith(".meta.json"):
            continue
        meta_path = h.with_suffix(h.suffix + ".meta.json")
        if not meta_path.exists():
            counters["no-meta"] += 1
            continue
        meta = json.loads(meta_path.read_text())
        try:
            ex = extract_one(h, meta)
        except Exception as e:
            log.write(f"ERR\t{h}\t{type(e).__name__}: {e}\n")
            counters["error"] += 1
            continue
        if ex is None:
            log.write(f"DROP\t{h}\tparking-or-empty\n")
            counters["dropped"] += 1
            continue

        # Dedup by Markdown content digest
        import hashlib
        digest = hashlib.sha1(ex.body_md.encode()).hexdigest()
        if digest in seen_digests:
            dup_log.write(f"{ex.source_url}\t->\t{seen_digests[digest]}\n")
            counters["dup-content"] += 1
            continue
        seen_digests[digest] = ex.source_url

        out = write_extracted(ex, used_slugs)
        log.write(f"OK\t{ex.era}\t{ex.collection}\t{out}\t<-\t{h}\n")
        counters[f"ok-{ex.era}-{ex.collection}"] += 1

        for img in ex.external_images:
            ext_log.write(f"{ex.source_url}\t{img}\n")

    log.close()
    ext_log.close()
    dup_log.close()

    print("Extraction summary:")
    for k, v in sorted(counters.items()):
        print(f"  {v:5d}  {k}")
    print(f"\n{sum(1 for _ in OUT.rglob('*.md'))} markdown files written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
