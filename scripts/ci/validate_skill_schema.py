#!/usr/bin/env python3
"""CI: Validate skill YAML frontmatter across all skill directories.

Replaces the original regex-based field detection with ``yaml.safe_load``
so that structurally invalid YAML (e.g. ``: `` inside a plain scalar,
backtick-leading list items, unclosed block scalars) is caught at CI
time, not silently shipped.

Scans every ``SKILL.md`` file (recursively) under the four skill
directories:

  - ``src/cohezion/skills/``      (PRIME skill definitions)
  - ``.claude/skills/``           (Claude Code skills)
  - ``.agents/skills/``           (canonical source of truth)
  - ``.pi/skills/``               (Pi harness skills)

Non-existent directories are skipped silently (e.g. ``.pi/skills/``
may not exist on all dev machines).

Checks for each ``SKILL.md``:
  - YAML frontmatter block (``--- ... ---``)
  - Parses cleanly under ``yaml.safe_load``
  - Required fields: ``name``, ``description`` (present and non-empty)

Exits 1 if any file fails so CI can catch schema drift before it
silently propagates.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SKILL_DIRS = [
    PROJECT_ROOT / "src" / "cohezion" / "skills",
    PROJECT_ROOT / ".claude" / "skills",
    PROJECT_ROOT / ".agents" / "skills",
    PROJECT_ROOT / ".pi" / "skills",
]
REQUIRED_FIELDS = ("name", "description")


@dataclass
class DirResult:
    """Validation results for a single skill directory."""

    dir: Path
    total: int = 0
    ok: int = 0
    missing_frontmatter: list[str] = field(default_factory=list)
    yaml_errors: list[tuple[str, str]] = field(default_factory=list)
    missing_fields: list[tuple[str, list[str]]] = field(default_factory=list)

    @property
    def failed(self) -> int:
        return self.total - self.ok


def _split_frontmatter(text: str) -> str | None:
    """Return the YAML block between ``---`` delimiters, or None."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i])
    return None


def _validate_file(path: Path) -> tuple[str | None, str | None, list[str] | None]:
    """Validate a single SKILL.md file.

    Returns a 3-tuple of (error_category, error_detail, missing_fields):
      - ``(None, None, None)``       → file is valid
      - ``("missing_frontmatter", None, None)`` → no ``---`` block found
      - ``("yaml_error", "<msg>", None)``       → YAML parse failure
      - ``("missing_fields", None, ["name", ...])`` → required fields absent
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    block = _split_frontmatter(text)
    if block is None:
        return "missing_frontmatter", None, None

    try:
        parsed = yaml.safe_load(block)
    except yaml.YAMLError as exc:
        parts: list[str] = [str(exc)]
        mark = getattr(exc, "problem_mark", None)
        if mark is not None:
            parts.append(f"  at line {mark.line + 1}, column {mark.column + 1}")
        problem = getattr(exc, "problem", None)
        if problem:
            parts.append(f"  problem: {problem}")
        return "yaml_error", "\n".join(parts), None

    if not isinstance(parsed, dict):
        return "yaml_error", "frontmatter is not a YAML mapping (got {type(parsed).__name__})", None

    absent = [f for f in REQUIRED_FIELDS if not parsed.get(f)]
    if absent:
        return "missing_fields", None, absent

    return None, None, None


def validate_dir(skill_dir: Path) -> DirResult:
    """Validate every SKILL.md file under *skill_dir* recursively."""
    result = DirResult(dir=skill_dir)
    if not skill_dir.is_dir():
        return result

    for path in sorted(skill_dir.rglob("SKILL.md")):
        result.total += 1
        cat, detail, missing = _validate_file(path)
        rel = str(path.relative_to(PROJECT_ROOT))
        if cat is None:
            result.ok += 1
        elif cat == "missing_frontmatter":
            result.missing_frontmatter.append(rel)
        elif cat == "yaml_error":
            result.yaml_errors.append((rel, detail or "unknown YAML error"))
        elif cat == "missing_fields":
            result.missing_fields.append((rel, missing or []))

    return result


def main() -> int:
    results: list[DirResult] = []
    for d in SKILL_DIRS:
        results.append(validate_dir(d))

    grand_total = sum(r.total for r in results)
    grand_ok = sum(r.ok for r in results)
    grand_failed = grand_total - grand_ok

    print(f"Skill directories scanned: {len([r for r in results if r.total > 0])}")
    print(f"SKILL.md files scanned:    {grand_total}")
    print(f"OK:                        {grand_ok}")
    if grand_failed:
        print(f"FAILED:                    {grand_failed}")
    print()

    failed = False

    for r in results:
        if r.total == 0:
            continue
        tag = "OK" if r.failed == 0 else "FAIL"
        print(f"[{tag}] {r.dir.relative_to(PROJECT_ROOT)} — {r.ok}/{r.total} OK")
        if r.missing_frontmatter:
            failed = True
            print(f"  missing frontmatter ({len(r.missing_frontmatter)}):")
            for name in r.missing_frontmatter[:20]:
                print(f"    - {name}")
            if len(r.missing_frontmatter) > 20:
                print(f"    ... and {len(r.missing_frontmatter) - 20} more")
        if r.yaml_errors:
            failed = True
            print(f"  YAML parse errors ({len(r.yaml_errors)}):")
            for name, detail in r.yaml_errors[:20]:
                print(f"    - {name}")
                for line in detail.splitlines():
                    print(f"        {line}")
            if len(r.yaml_errors) > 20:
                print(f"    ... and {len(r.yaml_errors) - 20} more")
        if r.missing_fields:
            failed = True
            print(f"  missing required fields ({len(r.missing_fields)}):")
            for name, absent in r.missing_fields[:20]:
                print(f"    - {name}: missing {', '.join(absent)}")
            if len(r.missing_fields) > 20:
                print(f"    ... and {len(r.missing_fields) - 20} more")

    if failed:
        print(f"\nRequired frontmatter fields: {', '.join(REQUIRED_FIELDS)}")
        print("Fix: add `|` block scalar indicator to fields containing ': ' or backticks")
        return 1

    print("\nOK: All SKILL.md files have valid YAML frontmatter with required fields")
    return 0


if __name__ == "__main__":
    sys.exit(main())