"""Register a plan markdown file in the SurrealDB traceability graph.

Usage::

    uv run python -m cohezion.traceability.register_plan <plan_file>

The script parses the markdown for tasks (``### Step N.N`` headings or
``- [ ] **N.N`` checkbox items), extracts the plan title from the first
``# Title`` line, derives a slug from the filename, and calls
``PlanGraph.create_plan()`` to persist the plan and its tasks.
"""

from __future__ import annotations

import asyncio
import logging
import re
import sys
from pathlib import Path

from cohezion.traceability.plan_graph import PlanGraph


logger = logging.getLogger(__name__)

# Patterns for detecting tasks in plan markdown
_STEP_HEADING = re.compile(r"^###\s+(\d+\.\d+[a-z]?)\b\s+(.*)", re.MULTILINE)
_CHECKBOX_STEP = re.compile(r"^-\s+\[[ x]\]\s+\*\*(\d+\.\d+[a-z]?)\b[.*]*\*\*\s*(.*)", re.MULTILINE)
_TITLE_LINE = re.compile(r"^#\s+(?:Plan:\s*)?(.+)", re.MULTILINE)


def parse_plan(text: str) -> tuple[str, list[dict[str, str]]]:
    """Parse a plan markdown file, returning (title, tasks).

    Each task is ``{"step_number": "0.1", "title": "Do the thing"}``.
    """
    # Extract title from first # heading
    title_match = _TITLE_LINE.search(text)
    title = title_match.group(1).strip() if title_match else "Untitled Plan"

    tasks: list[dict[str, str]] = []
    seen_steps: set[str] = set()

    # Collect from ### Step N.N headings
    for m in _STEP_HEADING.finditer(text):
        step = m.group(1)
        heading = m.group(2).strip()
        if step not in seen_steps:
            tasks.append({"step_number": step, "title": heading})
            seen_steps.add(step)

    # Collect from - [ ] **N.N ...** checkbox items
    for m in _CHECKBOX_STEP.finditer(text):
        step = m.group(1)
        heading = m.group(2).strip()
        if step not in seen_steps:
            tasks.append({"step_number": step, "title": heading})
            seen_steps.add(step)

    # Sort by step number for deterministic ordering
    tasks.sort(key=lambda t: _step_sort_key(t["step_number"]))
    return title, tasks


def slug_from_filename(path: str | Path) -> str:
    """Derive a plan slug from its filename.

    Strips date prefix (``YYYY-MM-DD-``) and ``.md`` extension.
    Examples::

        2026-03-30-webapp-fix.md  -> webapp-fix
        zazzy-snuggling-corbato.md -> zazzy-snuggling-corbato
    """
    stem = Path(path).stem
    # Strip leading date prefix if present
    stripped = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", stem)
    return stripped


async def register_plan(plan_path: str | Path) -> str:
    """Parse and register a plan file in SurrealDB. Returns the plan record id."""
    path = Path(plan_path)
    if not path.exists():
        raise FileNotFoundError(f"Plan file not found: {path}")

    text = path.read_text()
    title, tasks = parse_plan(text)
    slug = slug_from_filename(path)

    graph = PlanGraph()
    plan_id = await graph.create_plan(
        slug=slug,
        name=title,
        source_file=str(path),
        tasks=tasks,
    )
    logger.info("Registered plan %s (%s) with %d tasks.", slug, title, len(tasks))
    return plan_id


def _step_sort_key(step: str) -> tuple[int, int, str]:
    """Sort key for step numbers like '0.1', '0.1b', '1.2'."""
    parts = step.split(".")
    major = int(parts[0]) if parts[0].isdigit() else 0
    # Minor part may have a letter suffix like "1b"
    minor_str = parts[1] if len(parts) > 1 else "0"
    minor_digits = re.match(r"(\d+)(.*)", minor_str)
    if minor_digits:
        minor = int(minor_digits.group(1))
        suffix = minor_digits.group(2)
    else:
        minor = 0
        suffix = minor_str
    return (major, minor, suffix)


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <plan_file.md>", file=sys.stderr)
        sys.exit(1)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    plan_path = sys.argv[1]

    try:
        plan_id = asyncio.run(register_plan(plan_path))
        print(f"Registered: {plan_id}")
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to register plan: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
