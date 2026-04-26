#!/usr/bin/env python3
"""Dedup duplicate-title clusters within each collection.

For each cluster of files sharing (collection, lowercase(title)), pick one
canonical version and demote the rest to content/_cleanup/duplicates/<canonical-slug>/.

Canonical-picking rule:
  1. era == 'blogger'                    (latest, cleanest — 2019-2020 blog)
  2. era == 'drupal' with most-recent archivedAt   (2010-2020)
  3. era == 'static'                     (1996-2009 GeoCities-era HTML)

Tiebreakers within an era:
  more local_imgs > more ext_imgs > larger prose length

Outputs a per-cluster decision log for human review BEFORE any moves happen.

Usage:
    python3 tools/09_dedup_canonical.py            # dry-run, writes decision log only
    python3 tools/09_dedup_canonical.py --apply    # perform moves (DO NOT RUN until log is reviewed)
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
DUPES_DIR = CLEANUP / "duplicates"
COLLECTIONS = ["articles", "recipes", "varieties", "pages", "categories"]

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
EXT_IMG_RE = re.compile(r"!\[[^\]]*\]\((https?://\S+?)(?:\s+\"[^\"]*\")?\)")
LOCAL_IMG_RE = re.compile(r"!\[[^\]]*\]\(((?:/_assets|\./|\.\./)\S+?)(?:\s+\"[^\"]*\")?\)")

ERA_RANK = {"blogger": 0, "drupal": 1, "static": 2}


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


def canonical_sort_key(r: dict):
    """Lower is better. Sort ascending and pick index [0] as canonical."""
    fm = r["fm"]
    era = fm.get("era", "")
    era_rank = ERA_RANK.get(era, 99)
    archived = fm.get("archivedAt", "")
    # For drupal, MORE RECENT archivedAt wins -> negate by using neg-string compare;
    # easier: sort by negative timestamp via reverse string. Since we want max
    # archivedAt to be "smaller" (preferred), invert with a max-string trick.
    # Simplest: use -ord-like comparison; we want high archivedAt to be earlier
    # in sort order. Achieve by negating: use a tuple where the recency component
    # is a string we negate. Cleanest: invert via lambda for each criterion.
    # We'll return a tuple where smaller = better:
    #   (era_rank, -archived_recency, -local_imgs_count, -ext_imgs_count, -prose_len, filename)
    # archivedAt is like "2020-01-20T07:52:02Z" - lex sort works; we want max => negate.
    # Python can't negate strings, so transform: represent recency as the negative
    # of its sortable form. Trick: use the string itself but flip sign by sorting
    # descending on that field via tuple of (-1, archived) won't work either.
    # Simplest robust approach: use a list of comparators handled via reverse sort
    # on each axis. We'll just produce a tuple where we map archived to a number
    # if possible, else 0; bigger number = more recent = smaller key (negate).
    archived_num = 0
    if archived:
        # Convert "2020-01-20T07:52:02Z" -> integer YYYYMMDDhhmmss
        digits = re.sub(r"\D", "", archived)
        if digits:
            try:
                archived_num = int(digits[:14])
            except ValueError:
                archived_num = 0
    return (
        era_rank,
        -archived_num,
        -len(r["local_imgs"]),
        -len(r["ext_imgs"]),
        -len(r["prose"]),
        r["path"].name,
    )


def slugify_title(title: str) -> str:
    s = title.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s or "untitled"


def gather():
    rows = []
    for coll in COLLECTIONS:
        d = CONTENT / coll
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.md")):
            r = parse(p)
            if not r:
                continue
            r["collection"] = coll
            rows.append(r)
    return rows


def cluster(rows):
    by_key: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        title = r["fm"].get("title", "").strip().lower()
        if not title:
            continue
        key = (r["collection"], title)
        by_key.setdefault(key, []).append(r)
    return {k: v for k, v in by_key.items() if len(v) > 1}


def is_risky(canonical: dict, losers: list[dict]) -> list[str]:
    """Flag suspicious decisions. Returns list of warning strings."""
    flags = []
    cprose = len(canonical["prose"])
    clocal = len(canonical["local_imgs"])
    for lo in losers:
        lprose = len(lo["prose"])
        llocal = len(lo["local_imgs"])
        # Loser has substantially more prose
        if lprose > cprose * 1.5 and lprose - cprose > 200:
            flags.append(
                f"loser {lo['path'].name} has {lprose} prose vs canonical {cprose}"
            )
        # Loser has more local images
        if llocal > clocal:
            flags.append(
                f"loser {lo['path'].name} has {llocal} local imgs vs canonical {clocal}"
            )
    return flags


def reason_for_pick(canonical: dict, losers: list[dict]) -> str:
    fm = canonical["fm"]
    era = fm.get("era", "?")
    archived = fm.get("archivedAt", "")
    parts = [f"era={era}"]
    if era == "drupal" and archived:
        parts.append(f"archivedAt={archived}")
    # If tiebreaker mattered, mention it
    same_era = [r for r in [canonical] + losers if r["fm"].get("era") == era]
    if len(same_era) > 1:
        parts.append(
            f"local_imgs={len(canonical['local_imgs'])}, ext_imgs={len(canonical['ext_imgs'])}, prose={len(canonical['prose'])}"
        )
    return "; ".join(parts)


def write_log(decisions: list[dict], path: Path):
    lines = [
        "cluster_collection\tcluster_title\tcanonical\tcanonical_era\tcanonical_archivedAt\tcanonical_local_imgs\tcanonical_ext_imgs\tcanonical_prose\tdemoted\tdemoted_details\trisky_flags\treason"
    ]
    for d in decisions:
        c = d["canonical"]
        cfm = c["fm"]
        demoted_names = ";".join(lo["path"].name for lo in d["losers"])
        demoted_details = " | ".join(
            f"{lo['path'].name}[era={lo['fm'].get('era','?')},archivedAt={lo['fm'].get('archivedAt','')},local={len(lo['local_imgs'])},ext={len(lo['ext_imgs'])},prose={len(lo['prose'])}]"
            for lo in d["losers"]
        )
        risky = " ;; ".join(d["flags"]) if d["flags"] else ""
        lines.append(
            "\t".join([
                d["collection"],
                d["title"],
                c["path"].name,
                cfm.get("era", ""),
                cfm.get("archivedAt", ""),
                str(len(c["local_imgs"])),
                str(len(c["ext_imgs"])),
                str(len(c["prose"])),
                demoted_names,
                demoted_details,
                risky,
                d["reason"],
            ])
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_log_md(decisions: list[dict], path: Path):
    out = ["# Dedup decisions (dry-run)", ""]
    out.append(f"Total clusters: {len(decisions)}")
    out.append(
        f"Total files demoted: {sum(len(d['losers']) for d in decisions)}"
    )
    risky_count = sum(1 for d in decisions if d["flags"])
    out.append(f"Risky / manual-review clusters: {risky_count}")
    out.append("")
    out.append("---")
    out.append("")
    for d in sorted(decisions, key=lambda x: (bool(x["flags"]), x["collection"], x["title"]), reverse=True):
        c = d["canonical"]
        cfm = c["fm"]
        flag_marker = " RISKY" if d["flags"] else ""
        out.append(f"## [{d['collection']}] {d['title']}{flag_marker}")
        out.append("")
        out.append(f"- **Canonical:** `{c['path'].name}` — {d['reason']}")
        out.append(f"  - era={cfm.get('era','')}, archivedAt={cfm.get('archivedAt','')}, local_imgs={len(c['local_imgs'])}, ext_imgs={len(c['ext_imgs'])}, prose={len(c['prose'])}")
        out.append("- **Demoted:**")
        for lo in d["losers"]:
            lfm = lo["fm"]
            out.append(
                f"  - `{lo['path'].name}` — era={lfm.get('era','')}, archivedAt={lfm.get('archivedAt','')}, local_imgs={len(lo['local_imgs'])}, ext_imgs={len(lo['ext_imgs'])}, prose={len(lo['prose'])}"
            )
        if d["flags"]:
            out.append("- **Flags:**")
            for f in d["flags"]:
                out.append(f"  - {f}")
        out.append("")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def annotate_frontmatter(text: str, canonical_name: str, collection: str) -> str:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return text
    fm_raw, body = m.group(1), m.group(2)
    extras = []
    if "cleanupReason:" not in fm_raw:
        extras.append("cleanupReason: duplicate-title")
    if "originalCollection:" not in fm_raw:
        extras.append(f"originalCollection: {collection}")
    if "canonicalFile:" not in fm_raw:
        extras.append(f"canonicalFile: {canonical_name}")
    if not extras:
        return text
    return f"---\n{fm_raw}\n" + "\n".join(extras) + f"\n---\n{body}"


def apply_moves(decisions: list[dict]):
    DUPES_DIR.mkdir(parents=True, exist_ok=True)
    moved_rows = []
    for d in decisions:
        canonical_slug = slugify_title(d["title"])
        cluster_dir = DUPES_DIR / canonical_slug
        cluster_dir.mkdir(parents=True, exist_ok=True)
        for lo in d["losers"]:
            collection = d["collection"]
            # Annotate BEFORE git mv so changes land in the staged rename
            text = lo["path"].read_text(encoding="utf-8")
            text = annotate_frontmatter(text, d["canonical"]["path"].name, collection)
            lo["path"].write_text(text, encoding="utf-8")
            dest_name = lo["path"].name
            # Disambiguate identical basenames across collections (rare but possible)
            if (cluster_dir / dest_name).exists():
                dest_name = f"{collection}__{lo['path'].name}"
            dest = cluster_dir / dest_name
            subprocess.run(
                ["git", "mv", str(lo["path"]), str(dest)],
                cwd=ROOT,
                check=True,
            )
            moved_rows.append({
                "collection": collection,
                "original_path": str(lo["path"].relative_to(CONTENT)),
                "title": lo["fm"].get("title", ""),
                "canonical": d["canonical"]["path"].name,
                "dest": str(dest.relative_to(CONTENT)),
            })

    # Append to MANIFEST.tsv (preserve prior rows)
    manifest_path = CLEANUP / "MANIFEST.tsv"
    new_lines = []
    for r in moved_rows:
        # Match the existing manifest schema columns:
        # category  original_path  title  source_url  wayback_url  broken_images
        # We use category=duplicate-title and stash canonical name in broken_images slot
        # for traceability since we don't have a clean dedicated column.
        new_lines.append(
            "\t".join([
                "duplicate-title",
                r["original_path"],
                r["title"],
                "",  # source_url — could pull from frontmatter; leaving blank is fine, original still has it
                "",
                f"canonical={r['canonical']}",
            ])
        )
    if manifest_path.exists():
        existing = manifest_path.read_text(encoding="utf-8").rstrip("\n").splitlines()
        recorded = {ln.split("\t", 2)[1] for ln in existing[1:] if "\t" in ln}
        appended = [ln for ln in new_lines if ln.split("\t", 2)[1] not in recorded]
        all_lines = existing + appended
    else:
        header = "category\toriginal_path\ttitle\tsource_url\twayback_url\tbroken_images"
        all_lines = [header] + new_lines
    manifest_path.write_text("\n".join(all_lines) + "\n", encoding="utf-8")
    print(f"Moved {len(moved_rows)} files into {DUPES_DIR.relative_to(ROOT)}/")
    print(f"Manifest updated at {manifest_path.relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="perform moves (review log first!)")
    args = ap.parse_args()

    rows = gather()
    clusters = cluster(rows)
    if not clusters:
        print("No duplicate-title clusters found.")
        return 0

    decisions = []
    for (coll, title), group in clusters.items():
        ranked = sorted(group, key=canonical_sort_key)
        canonical = ranked[0]
        losers = ranked[1:]
        flags = is_risky(canonical, losers)
        decisions.append({
            "collection": coll,
            "title": title,
            "canonical": canonical,
            "losers": losers,
            "reason": reason_for_pick(canonical, losers),
            "flags": flags,
        })

    decisions.sort(key=lambda d: (d["collection"], d["title"]))

    tools_dir = ROOT / "tools"
    tsv_path = tools_dir / "_dedup_decisions.tsv"
    md_path = tools_dir / "_dedup_decisions.md"
    write_log(decisions, tsv_path)
    write_log_md(decisions, md_path)

    total_demoted = sum(len(d["losers"]) for d in decisions)
    risky = [d for d in decisions if d["flags"]]
    print(f"Clusters: {len(decisions)}")
    print(f"Total files that would be demoted: {total_demoted}")
    print(f"Risky / manual-review clusters: {len(risky)}")
    print(f"Decision log written to:")
    print(f"  {tsv_path.relative_to(ROOT)}")
    print(f"  {md_path.relative_to(ROOT)}")

    if risky:
        print("\nRisky clusters:")
        for d in risky:
            print(f"  [{d['collection']}] {d['title']}")
            for f in d["flags"]:
                print(f"    - {f}")

    if not args.apply:
        print("\nDry-run only. Review the decision log, then re-run with --apply.")
        return 0

    apply_moves(decisions)
    return 0


if __name__ == "__main__":
    sys.exit(main())
