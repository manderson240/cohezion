"""Backfill YAML frontmatter into dark skill files from the auto-generated registry.

A skill .md with no `name`+`description` frontmatter is DARK — the capability-registry lookup can't
see it (CLAUDE.md L273: missing frontmatter = silent capability blackout). The capability-matrix
audit (docs/SKILLS_CAPABILITY_MATRIX_2026-06-02.md) found 62 such files, ALL of which have a
description in the auto-generated registry (src/cohezion/registry/skill_registry.json). This script
sources frontmatter from that registry — it never fabricates content.

Safe by construction:
  * Idempotent — skips any file that already starts with `---`.
  * Only PREPENDS frontmatter; the original body is byte-for-byte preserved after it.
  * Uses yaml.safe_dump so the emitted block is always valid YAML (handles colons/quotes in
    descriptions).
  * Skips (and reports) any dark file with no auto-gen description rather than inventing one.

Run: python scripts/maintenance/backfill_skill_frontmatter.py [--apply]
Without --apply it is a dry run (reports what it WOULD do).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "src" / "cohezion" / "skills"
REGISTRY = ROOT / "src" / "cohezion" / "registry" / "skill_registry.json"


def _index_by_basename(registry: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for entry in registry.values():
        p = entry.get("path", "")
        if p:
            out[os.path.basename(p)] = entry
    return out


def backfill(apply: bool) -> dict:
    registry = json.loads(REGISTRY.read_text())
    by_base = _index_by_basename(registry)
    fixed, skipped_has_fm, no_source, invalid = [], [], [], []

    for md in sorted(SKILLS.glob("*.md")):
        text = md.read_text()
        if text.startswith("---"):
            skipped_has_fm.append(md.name)
            continue
        entry = by_base.get(md.name)
        if not entry or not (entry.get("description") or "").strip():
            no_source.append(md.name)
            continue
        fm = {"name": entry.get("name") or md.stem, "description": entry["description"].strip()}
        if entry.get("keywords"):
            fm["keywords"] = entry["keywords"]
        block = "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---\n\n"
        # validate the block round-trips before touching the file
        parsed = yaml.safe_load(block.split("---", 2)[1])
        if not (parsed.get("name") and parsed.get("description")):
            invalid.append(md.name)
            continue
        if apply:
            md.write_text(block + text)
        fixed.append(md.name)

    return {
        "fixed": fixed,
        "skipped_has_frontmatter": len(skipped_has_fm),
        "no_source": no_source,
        "invalid": invalid,
    }


def main() -> int:
    apply = "--apply" in sys.argv
    r = backfill(apply)
    mode = "APPLIED" if apply else "DRY RUN (pass --apply to write)"
    print(f"backfill_skill_frontmatter — {mode}")
    print(f"  would-fix / fixed:        {len(r['fixed'])}")
    print(f"  already had frontmatter:  {r['skipped_has_frontmatter']}")
    print(f"  no auto-gen source:       {len(r['no_source'])} {r['no_source'][:5]}")
    print(f"  invalid (skipped):        {len(r['invalid'])} {r['invalid']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
