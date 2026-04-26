#!/usr/bin/env python3
"""Rewrite external image URLs in Markdown to point to local public/_assets/."""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

URL_MAP = Path("public/_assets/_url_map.json")
CONTENT = Path("content")


def main() -> int:
    if not URL_MAP.exists():
        print("Run 05_fetch_external_images.py first (no _url_map.json).", file=sys.stderr)
        return 1
    mapping = json.loads(URL_MAP.read_text())

    md_re = re.compile(r"(!\[[^\]]*\])\((\S+?)(\s+\"[^\"]*\")?\s*\)")
    hero_re = re.compile(r'^heroImage:\s*"?([^"\n]+)"?\s*$', re.MULTILINE)
    n_files = n_rewrites = 0

    for md in CONTENT.rglob("*.md"):
        text = md.read_text()
        original = text

        def repl(m: re.Match) -> str:
            nonlocal n_rewrites
            alt, url, title = m.group(1), m.group(2).strip(), m.group(3) or ""
            if url in mapping:
                n_rewrites += 1
                return f"{alt}(/_assets/{mapping[url]}{title})"
            return m.group(0)

        text = md_re.sub(repl, text)

        def hero_repl(m: re.Match) -> str:
            nonlocal n_rewrites
            url = m.group(1).strip().strip('"')
            if url in mapping:
                n_rewrites += 1
                return f"heroImage: /_assets/{mapping[url]}"
            return m.group(0)

        text = hero_re.sub(hero_repl, text)

        if text != original:
            md.write_text(text)
            n_files += 1

    print(f"rewrote {n_rewrites} image refs across {n_files} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
