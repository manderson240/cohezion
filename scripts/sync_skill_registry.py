#!/usr/bin/env python3
"""Sync `src/cohezion/skills/skill_registry.json` with actual skill files.

Non-destructive: preserves metadata (version, concepts, see_also) for entries
whose source file still exists. Adds minimal entries for newly-discovered
skills. Marks orphaned entries (registry has them but file is gone) with a
`status: archived` flag rather than deleting — preserves history.

Run:
    uv run python scripts/sync_skill_registry.py
    uv run python scripts/sync_skill_registry.py --dry-run   # preview only

Exit codes:
    0 — registry in sync (no writes needed) OR successfully updated
    1 — dry-run found drift but --dry-run set
    2 — IO / parse error

Idempotent: running twice in a row on a clean repo is a no-op.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "src" / "cohezion" / "skills"
REGISTRY_PATH = SKILLS_DIR / "skill_registry.json"


def discover_skill_files() -> dict[str, Path]:
    """Return {skill_name: file_path} for every skill file under SKILLS_DIR.

    Skill name = filename stem. Excludes:
    - __init__.py files (Python packaging markers)
    - skill_registry.json (the registry itself)
    - Nested directories' __init__ or non-skill auxiliary files
    """
    discovered: dict[str, Path] = {}
    for path in SKILLS_DIR.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".md", ".py"}:
            continue
        if path.name in {"__init__.py", "skill_registry.json"}:
            continue
        stem = path.stem
        if stem in discovered and discovered[stem].suffix == ".md":
            # Prefer .md over .py for the canonical registry source
            continue
        discovered[stem] = path
    return discovered


def load_existing(registry_path: Path) -> dict[str, dict]:
    if not registry_path.exists():
        return {}
    try:
        with registry_path.open() as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"error: failed to load {registry_path}: {exc}", file=sys.stderr)
        sys.exit(2)


def build_synced_registry(
    existing: dict[str, dict], discovered: dict[str, Path]
) -> tuple[dict[str, dict], dict[str, str]]:
    """Return (new_registry, stats) where stats describes the delta."""
    synced: dict[str, dict] = {}
    added: list[str] = []
    archived: list[str] = []
    preserved: list[str] = []

    for skill_name in sorted(set(existing.keys()) | set(discovered.keys())):
        if skill_name in discovered:
            rel_source = str(discovered[skill_name].relative_to(REPO_ROOT))
            if skill_name in existing:
                entry = dict(existing[skill_name])
                entry["source"] = rel_source
                entry.pop("status", None)  # un-archive if file returned
                synced[skill_name] = entry
                preserved.append(skill_name)
            else:
                synced[skill_name] = {
                    "version": "v1.0",
                    "concepts": [],
                    "see_also": [],
                    "source": rel_source,
                }
                added.append(skill_name)
        else:
            # Entry in registry but file gone: mark archived, preserve metadata
            entry = dict(existing[skill_name])
            entry["status"] = "archived"
            synced[skill_name] = entry
            archived.append(skill_name)

    stats = {
        "preserved": f"{len(preserved)} (file present, metadata kept)",
        "added": f"{len(added)} (new skill files: {', '.join(added[:5])}{'...' if len(added) > 5 else ''})",
        "archived": f"{len(archived)} (registry entry but file absent: {', '.join(archived[:5])}{'...' if len(archived) > 5 else ''})",
        "total": f"{len(synced)} total entries (was {len(existing)})",
    }
    return synced, stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print delta, do not write registry")
    args = parser.parse_args()

    if not SKILLS_DIR.exists():
        print(f"error: skills dir not found: {SKILLS_DIR}", file=sys.stderr)
        return 2

    existing = load_existing(REGISTRY_PATH)
    discovered = discover_skill_files()
    synced, stats = build_synced_registry(existing, discovered)

    print("=== Skill Registry Sync ===")
    for key, val in stats.items():
        print(f"  {key}: {val}")

    if synced == existing:
        print("\nAlready in sync.")
        return 0

    if args.dry_run:
        print("\n--dry-run set; registry not written")
        return 1

    with REGISTRY_PATH.open("w") as f:
        json.dump(synced, f, indent=2, sort_keys=True)
        f.write("\n")
    print(f"\nWrote {REGISTRY_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
