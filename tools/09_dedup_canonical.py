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


def archived_num_of(r: dict) -> int:
    archived = r["fm"].get("archivedAt", "")
    if not archived:
        return 0
    digits = re.sub(r"\D", "", archived)
    if not digits:
        return 0
    try:
        return int(digits[:14])
    except ValueError:
        return 0


def canonical_sort_key(r: dict):
    """Original rule key. Lower is better. era > archivedAt > local_imgs > ext_imgs > prose."""
    fm = r["fm"]
    era_rank = ERA_RANK.get(fm.get("era", ""), 99)
    return (
        era_rank,
        -archived_num_of(r),
        -len(r["local_imgs"]),
        -len(r["ext_imgs"]),
        -len(r["prose"]),
        r["path"].name,
    )


def prose_rich_sort_key(r: dict):
    """Prose-richest first. Tiebreak by era, local_imgs, archivedAt, filename."""
    return (
        -len(r["prose"]),
        ERA_RANK.get(r["fm"].get("era", ""), 99),
        -len(r["local_imgs"]),
        -archived_num_of(r),
        r["path"].name,
    )


def pick_canonical(group: list[dict], prose_threshold: float = 0.80) -> tuple[dict, dict, str]:
    """Refined rule.

    Returns (canonical, original_rule_canonical, decision_mode).
    decision_mode is one of:
      - "era-candidate" (era candidate prose >= threshold * max_prose)
      - "prose-richest" (era candidate too thin, fall back to richest)

    Algorithm:
      1. max_prose = max prose across cluster.
      2. era_candidate = ranked[0] under original rule.
      3. If era_candidate.prose >= threshold * max_prose: era wins.
      4. Else: prose-richest wins (with era/local_imgs/archivedAt tiebreakers).
    """
    ranked_original = sorted(group, key=canonical_sort_key)
    era_candidate = ranked_original[0]
    max_prose = max(len(r["prose"]) for r in group)
    if max_prose == 0:
        return era_candidate, era_candidate, "era-candidate"
    if len(era_candidate["prose"]) >= prose_threshold * max_prose:
        return era_candidate, era_candidate, "era-candidate"
    richest = sorted(group, key=prose_rich_sort_key)[0]
    return richest, era_candidate, "prose-richest"


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


def is_risky(canonical: dict, losers: list[dict], original_canonical: dict, decision_mode: str) -> list[str]:
    """Flag suspicious decisions. Returns list of warning strings."""
    flags = []
    cprose = len(canonical["prose"])
    clocal = len(canonical["local_imgs"])
    # Disagreement between original era-priority rule and refined rule
    if original_canonical["path"].name != canonical["path"].name:
        flags.append(
            f"rule-change: refined rule picks {canonical['path'].name}; original era-priority would pick {original_canonical['path'].name}"
        )
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
        # Close-call: prose within 10% AND local_imgs >= canonical's
        if cprose > 0 and 0.90 * cprose <= lprose <= 1.10 * cprose and llocal >= clocal and lo["path"].name != canonical["path"].name:
            # only flag when era differs (genuine ambiguity)
            if lo["fm"].get("era") != canonical["fm"].get("era"):
                flags.append(
                    f"close-call: loser {lo['path'].name} prose={lprose} local={llocal} ~= canonical prose={cprose} local={clocal} (different eras)"
                )
    return flags


def reason_for_pick(canonical: dict, losers: list[dict], decision_mode: str, max_prose: int) -> str:
    fm = canonical["fm"]
    era = fm.get("era", "?")
    archived = fm.get("archivedAt", "")
    cprose = len(canonical["prose"])
    parts = [f"mode={decision_mode}", f"era={era}"]
    if era == "drupal" and archived:
        parts.append(f"archivedAt={archived}")
    if max_prose > 0:
        parts.append(f"prose={cprose} ({cprose/max_prose:.0%} of max {max_prose})")
    same_era = [r for r in [canonical] + losers if r["fm"].get("era") == era]
    if len(same_era) > 1:
        parts.append(
            f"local_imgs={len(canonical['local_imgs'])}, ext_imgs={len(canonical['ext_imgs'])}"
        )
    return "; ".join(parts)


def write_log(decisions: list[dict], path: Path):
    lines = [
        "cluster_collection\tcluster_title\tcanonical\tcanonical_era\tcanonical_archivedAt\tcanonical_local_imgs\tcanonical_ext_imgs\tcanonical_prose\tdecision_mode\toriginal_rule_pick\trule_changed\tdemoted\tdemoted_details\trisky_flags\treason"
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
        rule_changed = "yes" if d["original_canonical"]["path"].name != c["path"].name else "no"
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
                d["decision_mode"],
                d["original_canonical"]["path"].name,
                rule_changed,
                demoted_names,
                demoted_details,
                risky,
                d["reason"],
            ])
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_log_md(decisions: list[dict], path: Path):
    total_demoted = sum(len(d['losers']) for d in decisions)
    risky_count = sum(1 for d in decisions if d["flags"])
    changed_count = sum(1 for d in decisions if d["original_canonical"]["path"].name != d["canonical"]["path"].name)

    out = ["# Dedup decisions (dry-run, refined rule)", ""]
    out.append("Refined rule: era priority (blogger > recent-drupal > static) wins")
    out.append("ONLY IF the era candidate's prose is >= 80% of the cluster max.")
    out.append("Otherwise: pick the prose-richest member, era-then-imgs-then-archivedAt tiebreaks.")
    out.append("")
    out.append(f"- Total clusters: {len(decisions)}")
    out.append(f"- Total files demoted: {total_demoted}")
    out.append(f"- Choices changed vs. original era-priority rule: {changed_count}")
    out.append(f"- Risky / manual-review clusters: {risky_count}")
    out.append("")
    out.append("---")
    out.append("")

    # Section 1: clusters where the choice CHANGED vs. original rule
    changed = [d for d in decisions if d["original_canonical"]["path"].name != d["canonical"]["path"].name]
    if changed:
        out.append("## Clusters where the refined rule CHANGED the choice")
        out.append("")
        for d in sorted(changed, key=lambda x: (x["collection"], x["title"])):
            _emit_cluster(out, d, header_prefix="### ")
        out.append("---")
        out.append("")

    # Section 2: still-RISKY but unchanged choice
    still_risky = [d for d in decisions if d["flags"] and d["original_canonical"]["path"].name == d["canonical"]["path"].name]
    if still_risky:
        out.append("## Still RISKY (choice unchanged but flagged for review)")
        out.append("")
        for d in sorted(still_risky, key=lambda x: (x["collection"], x["title"])):
            _emit_cluster(out, d, header_prefix="### ")
        out.append("---")
        out.append("")

    # Section 3: clean clusters
    clean = [d for d in decisions if not d["flags"]]
    if clean:
        out.append("## Clean clusters (no flags)")
        out.append("")
        for d in sorted(clean, key=lambda x: (x["collection"], x["title"])):
            _emit_cluster(out, d, header_prefix="### ")

    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def _emit_cluster(out: list[str], d: dict, header_prefix: str = "## "):
    c = d["canonical"]
    cfm = c["fm"]
    flag_marker = " RISKY" if d["flags"] else ""
    out.append(f"{header_prefix}[{d['collection']}] {d['title']}{flag_marker}")
    out.append("")
    out.append(f"- **Canonical:** `{c['path'].name}` — {d['reason']}")
    out.append(f"  - era={cfm.get('era','')}, archivedAt={cfm.get('archivedAt','')}, local_imgs={len(c['local_imgs'])}, ext_imgs={len(c['ext_imgs'])}, prose={len(c['prose'])}")
    if d["original_canonical"]["path"].name != c["path"].name:
        oc = d["original_canonical"]
        ofm = oc["fm"]
        out.append(f"- **Original-rule pick (overridden):** `{oc['path'].name}` — era={ofm.get('era','')}, archivedAt={ofm.get('archivedAt','')}, local_imgs={len(oc['local_imgs'])}, ext_imgs={len(oc['ext_imgs'])}, prose={len(oc['prose'])}")
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
        canonical, original_canonical, decision_mode = pick_canonical(group)
        losers = [r for r in group if r["path"].name != canonical["path"].name]
        # Stable order for losers
        losers.sort(key=canonical_sort_key)
        max_prose = max(len(r["prose"]) for r in group)
        flags = is_risky(canonical, losers, original_canonical, decision_mode)
        decisions.append({
            "collection": coll,
            "title": title,
            "canonical": canonical,
            "original_canonical": original_canonical,
            "decision_mode": decision_mode,
            "losers": losers,
            "reason": reason_for_pick(canonical, losers, decision_mode, max_prose),
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
    changed = [d for d in decisions if d["original_canonical"]["path"].name != d["canonical"]["path"].name]
    print(f"Clusters: {len(decisions)}")
    print(f"Total files that would be demoted: {total_demoted}")
    print(f"Choices changed vs original era-priority rule: {len(changed)}")
    print(f"Risky / manual-review clusters: {len(risky)}")
    print(f"Decision log written to:")
    print(f"  {tsv_path.relative_to(ROOT)}")
    print(f"  {md_path.relative_to(ROOT)}")

    if changed:
        print("\nClusters where the refined rule CHANGED the canonical:")
        for d in changed:
            print(f"  [{d['collection']}] {d['title']}")
            print(f"    refined => {d['canonical']['path'].name} (prose={len(d['canonical']['prose'])})")
            print(f"    original => {d['original_canonical']['path'].name} (prose={len(d['original_canonical']['prose'])})")

    if risky:
        print("\nRisky clusters (worst by max prose-gap to canonical):")
        def worst_gap(d):
            cprose = len(d["canonical"]["prose"])
            return max((len(lo["prose"]) - cprose) for lo in d["losers"]) if d["losers"] else 0
        for d in sorted(risky, key=worst_gap, reverse=True):
            gap = worst_gap(d)
            print(f"  [{d['collection']}] {d['title']} (gap={gap})")
            for f in d["flags"]:
                print(f"    - {f}")

    if not args.apply:
        print("\nDry-run only. Review the decision log, then re-run with --apply.")
        return 0

    apply_moves(decisions)
    return 0


if __name__ == "__main__":
    sys.exit(main())
