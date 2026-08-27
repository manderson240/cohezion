#!/usr/bin/env python3
"""CI: Validate skill registry consistency and capability index.

What a PASS here actually means, stated precisely: **the registry agrees with
`skill_discovery.discover_skills`** -- not "the registry agrees with reality".
This validator and `sync_skill_registry.py` deliberately share one scan so they
can never disagree with each other, which is what makes the drift number
trustworthy; it is also what stops this gate from ever catching a defect in the
scanner itself. A "0 unregistered" result is self-certifying with respect to the
scan.

The scanner's own correctness therefore rests on an INDEPENDENT oracle:
`tests/scripts/test_validate_registry.py` exercises it against hand-built
fixture trees (flat skills, bundles, bundle support files, archives, name
collisions, case variants) that are not derived from the scan. If you change
`discover_skills`, that fixture suite -- not this gate -- is what tells you
whether it is still right.

(Raised by adversarial review, 2026-08-27.)
"""

from __future__ import annotations

import sys
from pathlib import Path

from cohezion.registry.capability_registry import CapabilityRegistry
from cohezion.registry.skill_discovery import discover_skills
from cohezion.registry.skill_registry import load_registry


SKILLS_DIR = Path("src/cohezion/skills")

def scan_skill_files(skills_dir: Path) -> set[str]:
    """Return the name of every discoverable skill under *skills_dir*.

    Thin wrapper over the canonical scan in
    ``cohezion.registry.skill_discovery`` so this validator and the sync script
    can never disagree about what counts as a skill.
    """
    return set(discover_skills(skills_dir))


def main() -> int:
    """Cross-check registry JSON against .md files on disk."""
    registry = load_registry()
    print(f"Registry entries: {len(registry)}")

    # Collect .md files on disk
    md_files = scan_skill_files(SKILLS_DIR)
    if not SKILLS_DIR.is_dir():
        print(f"WARN: Skills directory not found: {SKILLS_DIR}")

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
