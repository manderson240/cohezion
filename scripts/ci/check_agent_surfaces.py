#!/usr/bin/env python3
"""Exclusive write-surface checker for Cohezion agent delegations.

Every repository path must resolve to exactly ONE owning agent per
AGENT-SURFACES.md (repo root). Resolution: longest matching glob wins; a
specificity tie between DIFFERENT owners is an error; no match is an error
(fail-closed -- the map must stay true as the repo grows).

Adopted from github.com/cbrock84/headcount (AGENT-SURFACES + check-all.sh).

Usage:
    python scripts/ci/check_agent_surfaces.py <path> [<path> ...]
    python scripts/ci/check_agent_surfaces.py --self-test   # prove it can go RED

Exit codes: 0 all paths owned; 1 unowned or ambiguous path; 2 map/usage error.

CI wiring: .github/workflows/agent-surfaces.yml runs --self-test, then this over
the PR-changed paths. The meta-gate scripts/ci/self_test_coverage.py (blocking in
ci.yml) RUNS every invoked gate's --self-test; until 2026-10-27 this was the one
gate without the flag, which kept that meta-gate red. Unit tests:
tests/unit/test_check_agent_surfaces.py.
"""

from __future__ import annotations

import fnmatch
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


MAP_PATH = Path(__file__).resolve().parents[2] / "AGENT-SURFACES.md"

_ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*(@[A-Za-z0-9_-]+)\s*\|")


@dataclass(frozen=True, slots=True)
class Surface:
    """One ownership row: glob pattern -> owning agent label."""

    pattern: str
    owner: str
    line: int


def parse_map(path: Path | str = MAP_PATH) -> list[Surface]:
    """Parse ownership table rows from the markdown map (no rows -> error)."""
    surfaces: list[Surface] = []
    text = Path(path).read_text(encoding="utf-8")
    for lineno, line in enumerate(text.splitlines(), 1):
        match = _ROW.match(line.strip())
        if match is not None:
            surfaces.append(Surface(match.group(1), match.group(2), lineno))
    return surfaces


def resolve_owner(path: str, surfaces: list[Surface]) -> tuple[str | None, list[Surface]]:
    """Resolve one path to its owner.

    Returns ``(owner, ties)``. ``(owner, [])`` on a clean hit; ``(None, [])``
    when nothing matches (unowned); ``(None, ties)`` when the most-specific
    matches disagree on the owner (ambiguous). Ties within one owner are not
    ambiguous -- duplicate rows for the same owner are harmless.
    """
    matches = [s for s in surfaces if fnmatch.fnmatchcase(path, s.pattern)]
    if not matches:
        return None, []
    best = max(len(s.pattern) for s in matches)
    top = [s for s in matches if len(s.pattern) == best]
    owners = {s.owner for s in top}
    if len(owners) == 1:
        return next(iter(owners)), []
    return None, top


def self_test() -> int:
    """Plant each defect the gate exists to catch against a throwaway map; require RED.

    Three verdicts the gate rests on, each checked against a map nobody else reads:
    an owned path resolves to its owner (GREEN), an unowned path resolves to nothing
    (RED), and a specificity tie between two owners is reported as a tie (RED). Plus
    the fail-closed edge: a map with no rows parses to nothing rather than to silence.
    """
    with tempfile.TemporaryDirectory() as tmp:
        planted = Path(tmp) / "AGENT-SURFACES.md"
        planted.write_text(
            "| Surface | Owner |\n|---|---|\n"
            "| `src/a/**` | @alpha |\n"
            "| `src/**/gen_*.py` | @alpha |\n"
            "| `src/xy/gen_*.py` | @beta |\n"
            "| `src/b/**` | @alpha |\n"
            "| `src/b/x.py` | @beta |\n",
            encoding="utf-8",
        )
        rows = parse_map(planted)
        empty = Path(tmp) / "EMPTY.md"
        empty.write_text("# no table here\n", encoding="utf-8")

        failures: list[str] = []
        if resolve_owner("src/a/x.py", rows) != ("@alpha", []):
            failures.append("owned path did not resolve to its owner (cannot go GREEN)")
        if resolve_owner("src/b/x.py", rows) != ("@beta", []):
            failures.append(
                "longest glob did not win (a shortest-wins mutant passes the other probes)"
            )
        if resolve_owner("docs/x.md", rows) != (None, []):
            failures.append("unowned path was not reported unowned (cannot go RED)")
        owner, ties = resolve_owner("src/xy/gen_1.py", rows)
        if owner is not None or {s.owner for s in ties} != {"@alpha", "@beta"}:
            failures.append("owner tie was not reported ambiguous (cannot go RED)")
        if parse_map(empty):
            failures.append("a map with no rows parsed to rows (fail-closed edge lost)")

    if failures:
        print("SELF-TEST FAILED:\n  " + "\n  ".join(failures), file=sys.stderr)
        return 1
    print("SELF-TEST OK: owned resolves, unowned is RED, owner tie is RED, empty map is empty.")
    return 0


def main(argv: list[str]) -> int:
    """CLI: resolve each path; exit 1 on unowned/ambiguous, 2 on map errors."""
    if argv == ["--self-test"]:
        return self_test()
    if not argv:
        print(
            f"usage: check_agent_surfaces.py <path> [<path> ...] (map: {MAP_PATH})",
            file=sys.stderr,
        )
        return 2
    surfaces = parse_map()
    if not surfaces:
        print(f"ERROR: no ownership rows parsed from {MAP_PATH}", file=sys.stderr)
        return 2
    failures: list[str] = []
    for raw in argv:
        # Strip a literal "./" prefix only -- never lstrip("./"), which would
        # also eat the leading dot of dotfile paths like .github/**.
        candidate = raw[2:] if raw.startswith("./") else raw
        owner, ties = resolve_owner(candidate, surfaces)
        if owner is None and not ties:
            failures.append(
                f"UNOWNED   {raw}  (no surface matches -- add a row to AGENT-SURFACES.md)"
            )
        elif owner is None:
            clash = " vs ".join(f"{s.owner} ({s.pattern})" for s in ties)
            failures.append(f"AMBIGUOUS {raw}  {clash}")
        else:
            print(f"{owner:18s} {raw}")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
