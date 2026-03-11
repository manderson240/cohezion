#!/usr/bin/env python3
"""
Triune Vault Metamorphosis — Rename directories to match the Triune Self architecture.

Phase 2 of the Triune Vault plan.

Usage:
    python3 scripts/triune-metamorphosis.py [--dry-run]
"""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent

# ─── Directory Rename Map ────────────────────────────────────────────────────
# Format: (old_name, new_name, aspect, description)
RENAMES = [
    # The Knower
    ("concepts", "cortex", "knower", "Definitions — what things ARE"),
    ("papers", "sensory", "knower", "External observations — what IS perceived"),
    ("lessons", "memory", "knower", "What IS remembered — embodied knowledge"),
    ("specs", "genome", "knower", "The blueprint — what the system IS"),
    # The Thinker
    ("decisions", "prefrontal", "thinker", "Executive function — deliberate choice"),
    ("experiments", "laboratory", "thinker", "Hypothesis testing — structured reasoning"),
    ("patterns", "cerebellum", "thinker", "Refined procedures — reason crystallized"),
    # The Doer
    ("projects", "motor", "doer", "Action plans — desire made concrete"),
    ("inbox", "thalamus", "doer", "Sensory relay — incoming stimulus"),
    # The Connective
    ("canvas", "visual-cortex", "connective", "Spatial reasoning, diagrams"),
]

# Directories to merge into hippocampus
HIPPOCAMPUS_SOURCES = ["daily", "sessions"]

# New directories to create (no rename source)
NEW_DIRS = [
    ("subconscious", "connective", "SurrealDB-generated latent associations"),
    ("dreaming", "connective", "The Everlasting Now — cross-domain resonances"),
    ("metabolism", "connective", "Whole-system health dashboards"),
    ("songlines", "connective", "Narrative knowledge paths across Country"),
]

# Path-prefix regex for wiki-links
PATH_LINK_RE = re.compile(r"\[\[((?:[a-zA-Z0-9_\-]+)/[^\]|#]+?)([|#][^\]]*?)?\]\]")

# Old->new directory name mapping for link fixes
OLD_TO_NEW = {old: new for old, new, _, _ in RENAMES}
OLD_TO_NEW["daily"] = "hippocampus"
OLD_TO_NEW["sessions"] = "hippocampus"


def fix_path_prefixed_links(text: str) -> tuple[str, int]:
    """Fix path-prefixed wiki-links to use new directory names."""
    count = 0

    def replace_link(match):
        nonlocal count
        target = match.group(1)
        suffix = match.group(2) or ""
        parts = target.split("/", 1)
        if len(parts) == 2 and parts[0] in OLD_TO_NEW:
            count += 1
            return f"[[{OLD_TO_NEW[parts[0]]}/{parts[1]}{suffix}]]"
        return match.group(0)

    return PATH_LINK_RE.sub(replace_link, text), count


def create_index_file(directory: Path, name: str, aspect: str, description: str) -> str:
    """Generate _index.md content for a directory."""
    aspect_names = {
        "knower": "The Knower (I-ness, Selfness)",
        "thinker": "The Thinker (Rightness, Reason)",
        "doer": "The Doer (Feeling, Desire)",
        "connective": "The Connective (Where All Three Meet)",
    }
    return f"""---
title: "{name}/ — {description}"
date: 2026-03-09
tags: [vault-architecture, triune-self, {aspect}]
aspect: {aspect}
---

# {name}/

> **Aspect:** {aspect_names.get(aspect, aspect)}
> **Purpose:** {description}

This directory is part of the **{aspect_names.get(aspect, aspect)}** aspect of the Triune Vault.
"""


def main():
    parser = argparse.ArgumentParser(description="Triune Vault Metamorphosis")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    prefix = "[DRY RUN] " if args.dry_run else ""

    # Phase 1: Rename directories
    print(f"\n{prefix}=== Phase 1: Directory Renames ===\n")
    for old, new, aspect, desc in RENAMES:
        old_path = VAULT / old
        new_path = VAULT / new
        if old_path.exists():
            if new_path.exists():
                print(f"  SKIP {old} -> {new} (target exists)")
            else:
                print(f"  {prefix}RENAME {old}/ -> {new}/")
                if not args.dry_run:
                    old_path.rename(new_path)
        else:
            print(f"  SKIP {old} (not found)")

    # Phase 2: Merge daily + sessions into hippocampus
    print(f"\n{prefix}=== Phase 2: Merge into hippocampus/ ===\n")
    hippo = VAULT / "hippocampus"
    if not args.dry_run:
        hippo.mkdir(exist_ok=True)

    for source in HIPPOCAMPUS_SOURCES:
        src_path = VAULT / source
        if src_path.exists():
            file_count = sum(1 for f in src_path.rglob("*") if f.is_file())
            print(f"  {prefix}MERGE {source}/ ({file_count} files) -> hippocampus/")
            if not args.dry_run:
                for item in src_path.iterdir():
                    dest = hippo / item.name
                    if dest.exists():
                        # Prefix with source directory to avoid collision
                        dest = hippo / f"{source}-{item.name}"
                    if item.is_dir():
                        shutil.copytree(item, dest)
                    else:
                        shutil.copy2(item, dest)
                shutil.rmtree(src_path)
        else:
            print(f"  SKIP {source} (not found)")

    # Phase 3: Create new directories
    print(f"\n{prefix}=== Phase 3: Create New Directories ===\n")
    for name, aspect, desc in NEW_DIRS:
        dir_path = VAULT / name
        if dir_path.exists():
            print(f"  SKIP {name}/ (already exists)")
        else:
            print(f"  {prefix}CREATE {name}/")
            if not args.dry_run:
                dir_path.mkdir(exist_ok=True)

    # Phase 4: Create _index.md files for all new/renamed directories
    print(f"\n{prefix}=== Phase 4: Create _index.md Files ===\n")
    all_dirs = [(new, aspect, desc) for _, new, aspect, desc in RENAMES]
    all_dirs.append(("hippocampus", "doer", "Episodic memory — lived experience"))
    all_dirs.extend([(name, aspect, desc) for name, aspect, desc in NEW_DIRS])

    for name, aspect, desc in all_dirs:
        dir_path = VAULT / name
        index_path = dir_path / "_index.md"
        if dir_path.exists() and not index_path.exists():
            print(f"  {prefix}CREATE {name}/_index.md")
            if not args.dry_run:
                index_path.write_text(create_index_file(dir_path, name, aspect, desc))
        elif index_path.exists():
            print(f"  SKIP {name}/_index.md (exists)")
        else:
            print(f"  SKIP {name}/_index.md (dir not found)")

    # Phase 5: Fix path-prefixed wiki-links
    print(f"\n{prefix}=== Phase 5: Fix Path-Prefixed Wiki-Links ===\n")
    total_fixed = 0
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in {
            "node_modules", ".worktrees", "tools", "obsidian-plugin", "mcp-server"
        }]
        for fname in files:
            if not fname.endswith(".md"):
                continue
            fpath = Path(root) / fname
            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            fixed_text, count = fix_path_prefixed_links(text)
            if count > 0:
                rel = fpath.relative_to(VAULT)
                print(f"  {prefix}FIX {rel}: {count} link(s)")
                total_fixed += count
                if not args.dry_run:
                    fpath.write_text(fixed_text, encoding="utf-8")

    print(f"\n  Total links fixed: {total_fixed}")

    # Summary
    print(f"\n{prefix}=== Summary ===")
    print(f"  Directories renamed: {len(RENAMES)}")
    print(f"  Directories merged: {len(HIPPOCAMPUS_SOURCES)} -> hippocampus/")
    print(f"  New directories created: {len(NEW_DIRS)}")
    print(f"  Index files created: {len(all_dirs)}")
    print(f"  Wiki-links fixed: {total_fixed}")

    if args.dry_run:
        print(f"\n  [DRY RUN] No changes made. Run without --dry-run to execute.")
    else:
        print(f"\n  Metamorphosis complete.")


if __name__ == "__main__":
    main()
