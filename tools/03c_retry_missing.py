#!/usr/bin/env python3
"""Retry HTML pages that didn't land on disk after the main download."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from importlib import import_module
mod = import_module("03_download")
import time

raw = Path("raw")
todo: list[tuple[str, str]] = []
for line in Path("tools/keep_html.tsv").read_text().splitlines():
    if not line.strip():
        continue
    ts, url, _ = line.split("\t")
    p = mod.safe_local_path(raw, url, "text/html")
    if not p.exists():
        todo.append((ts, url))

print(f"retrying {len(todo)} missing pages")
log = (raw / "_download.log").open("a")
log.write(f"\n=== retry @ {time.strftime('%Y-%m-%d %H:%M:%S')} ({len(todo)} items) ===\n")
n_ok = n_fail = 0
for i, (ts, url) in enumerate(todo, 1):
    dest = mod.safe_local_path(raw, url, "text/html")
    ok, msg = mod.fetch(ts, url, dest, retries=6)
    log.write(f"{'OK' if ok else 'FAIL'}\thtml\t{ts}\t{url}\t{msg}\n")
    log.flush()
    if ok:
        n_ok += 1
    else:
        n_fail += 1
    if i % 10 == 0 or i == len(todo):
        print(f"[{i}/{len(todo)}] ok={n_ok} fail={n_fail}", flush=True)
    time.sleep(0.4)
log.close()
print(f"Done. ok={n_ok} fail={n_fail}")
