#!/usr/bin/env python3
"""Migrate existing extensionless HTML files to <name>/index.html."""
from pathlib import Path
import sys, tempfile
sys.path.insert(0, str(Path(__file__).parent))
from importlib import import_module
mod = import_module("03_download")  # type: ignore

raw = Path("raw")
moved = collisions = 0
for line in Path("tools/keep_html.tsv").read_text().splitlines():
    if not line.strip():
        continue
    ts, url, _ = line.split("\t")
    old = mod.old_local_path(raw, url)
    new = mod.safe_local_path(raw, url, "text/html")
    if old == new:
        continue
    if not old.exists() or not old.is_file():
        continue
    # old is a file at e.g. raw/host/foo, new is raw/host/foo/index.html.
    # Move old aside, create dir, drop file as index.html.
    tmp = old.with_suffix(old.suffix + ".__tmp__")
    old.rename(tmp)
    new.parent.mkdir(parents=True, exist_ok=True)
    tmp.rename(new)
    old_meta = old.with_suffix(old.suffix + ".meta.json")
    if old_meta.exists():
        old_meta.rename(new.with_suffix(new.suffix + ".meta.json"))
    moved += 1
print(f"moved={moved} collisions_dropped={collisions}")
