#!/usr/bin/env python3
"""Pre-commit hook: enforce that files matching .gitattributes LFS patterns
are committed as LFS pointers, not as their full binary content.

Called by .pre-commit-config.yaml with the list of staged files as argv. Exits
1 if any matching file >1 KiB is not an LFS pointer (i.e. does not begin with
`version https://git-lfs`).

Extracted from an inline `python -c "..."` block in .pre-commit-config.yaml
on 2026-04-22 — the inline form had an embedded multi-line Python string that
wasn't YAML-safe (unindented continuation lines looked like new YAML keys to
the parser). Extracting to a script makes the hook YAML-format-agnostic and
unit-testable.

Non-zero exit blocks the commit; guidance message tells the user how to fix.
"""

from __future__ import annotations

import sys
from pathlib import Path


LFS_POINTER_MAGIC = b"version https://git-lfs"
MIN_CHECK_BYTES = 1024  # skip files smaller than this — not worth LFS tracking


def lfs_patterns_from_gitattributes(gitattributes_path: Path) -> list[str]:
    """Parse `.gitattributes` and return the pattern tokens that have `filter=lfs`."""
    if not gitattributes_path.exists():
        return []
    patterns = []
    for line in gitattributes_path.read_text().splitlines():
        if "filter=lfs" in line:
            tokens = line.split()
            if tokens:
                patterns.append(tokens[0])
    return patterns


def matches_any(path: str, patterns: list[str]) -> bool:
    """True if `path` matches any of the LFS glob patterns. Kept simple to match
    the original inline heuristic: strip leading '*' and check suffix."""
    return any(path.endswith(p.lstrip("*")) for p in patterns)


def is_lfs_pointer(path: Path) -> bool:
    """True if the file's first 50 bytes begin with the LFS pointer magic."""
    with path.open("rb") as fh:
        head = fh.read(50)
    return head.startswith(LFS_POINTER_MAGIC)


def main(argv: list[str]) -> int:
    patterns = lfs_patterns_from_gitattributes(Path(".gitattributes"))
    if not patterns:
        return 0  # no LFS config to enforce

    errors: list[str] = []
    for arg in argv:
        path = Path(arg)
        if not path.exists() or not path.is_file():
            continue
        if not matches_any(arg, patterns):
            continue
        size = path.stat().st_size
        if size <= MIN_CHECK_BYTES:
            continue
        if not is_lfs_pointer(path):
            size_mb = size / 1048576
            errors.append(f"{arg} ({size_mb:.0f}MB) matches LFS pattern but is NOT an LFS pointer")

    for e in errors:
        print(f"ERROR: {e}")
        print("  Run: git lfs install && git add --renormalize .")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
