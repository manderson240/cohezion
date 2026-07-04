#!/usr/bin/env python3
"""CI: Validate PRIME skill YAML frontmatter for required fields (Pinterest drift-check pattern).

Checks every .md file under src/cohezion/skills/ for:
  - YAML frontmatter block (--- ... ---)
  - Required fields: name, description

Exits 1 if any skill is missing required fields so CI can catch schema drift
before it silently propagates (analogous to Pinterest's additive-schema guard).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent.parent / "src" / "cohezion" / "skills"
REQUIRED_FIELDS = ("name", "description")
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_FIELD_RE = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_-]*):", re.MULTILINE)


def _extract_frontmatter_fields(text: str) -> set[str]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return set()
    return set(_FIELD_RE.findall(m.group(1)))


def main() -> int:
    skill_files = sorted(SKILLS_DIR.glob("*.md"))
    if not skill_files:
        print(f"FAIL: No skill files found under {SKILLS_DIR}")
        return 1

    missing_frontmatter: list[str] = []
    missing_fields: list[tuple[str, list[str]]] = []

    for path in skill_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        fields = _extract_frontmatter_fields(text)
        if not fields:
            missing_frontmatter.append(path.name)
            continue
        absent = [f for f in REQUIRED_FIELDS if f not in fields]
        if absent:
            missing_fields.append((path.name, absent))

    total = len(skill_files)
    ok = total - len(missing_frontmatter) - len(missing_fields)

    print(f"Skills scanned:          {total}")
    print(f"Frontmatter present:     {total - len(missing_frontmatter)}")
    print(f"All required fields:     {ok}")

    failed = False

    if missing_frontmatter:
        print(f"\nFAIL: {len(missing_frontmatter)} skill(s) have no YAML frontmatter:")
        for name in missing_frontmatter[:20]:
            print(f"  - {name}")
        if len(missing_frontmatter) > 20:
            print(f"  ... and {len(missing_frontmatter) - 20} more")
        failed = True

    if missing_fields:
        print(f"\nFAIL: {len(missing_fields)} skill(s) missing required frontmatter field(s):")
        for name, absent in missing_fields[:20]:
            print(f"  - {name}: missing {', '.join(absent)}")
        if len(missing_fields) > 20:
            print(f"  ... and {len(missing_fields) - 20} more")
        failed = True

    if failed:
        print(
            "\nRequired frontmatter fields: "
            + ", ".join(REQUIRED_FIELDS)
        )
        return 1

    print("OK: All skills have required YAML frontmatter fields")
    return 0


if __name__ == "__main__":
    sys.exit(main())
