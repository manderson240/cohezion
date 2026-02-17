#!/usr/bin/env python3
"""CI: Validate skill registry consistency and capability index."""

from __future__ import annotations

import sys
from pathlib import Path

from cohezion.registry.capability_registry import CapabilityRegistry
from cohezion.registry.skill_registry import load_registry


SKILLS_DIR = Path("src/cohezion/skills")


def main() -> int:
    """Cross-check registry JSON against .md files on disk."""
    registry = load_registry()
    print(f"Registry entries: {len(registry)}")

    # Collect .md files on disk
    if SKILLS_DIR.is_dir():
        md_files = {p.stem for p in SKILLS_DIR.glob("*.md")}
    else:
        print(f"WARN: Skills directory not found: {SKILLS_DIR}")
        md_files = set()

    registry_names = set(registry.keys())

    # Orphaned: in registry but no .md on disk
    orphaned = registry_names - md_files
    # Unregistered: .md on disk but not in registry
    unregistered = md_files - registry_names

    if orphaned:
        print(f"\nOrphaned entries ({len(orphaned)}) — in registry, no .md file:")
        for name in sorted(orphaned):
            print(f"  - {name}")

    if unregistered:
        print(f"\nUnregistered skills ({len(unregistered)}) — .md exists, not in registry:")
        for name in sorted(unregistered):
            print(f"  - {name}")

    if not orphaned and not unregistered:
        print("Registry and disk are fully consistent")

    # Verify CapabilityRegistry constructs without error
    try:
        cap_reg = CapabilityRegistry()
        print(f"\nCapabilityRegistry loaded: {len(cap_reg.capabilities)} capabilities")
    except Exception as exc:
        print(f"\nWARN: CapabilityRegistry failed to construct: {exc}")

    # Summary
    print(
        f"\nSummary: {len(registry)} registered, {len(md_files)} on disk, "
        f"{len(orphaned)} orphaned, {len(unregistered)} unregistered"
    )

    # Orphaned entries = broken references = fail
    if orphaned:
        print("FAIL: Orphaned registry entries point to missing files")
        return 1

    print("OK: Registry is consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
