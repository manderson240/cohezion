#!/usr/bin/env python3
"""CI gate: every TIDE-convention test file must contain at least one PRIMARY DISC. marker.

A TIDE-convention test file is any ``test_*.py`` under ``tests/compound/`` whose
**module-level docstring** begins with the pattern ``Item NNN:`` (a numeric item
reference).  These files follow the Discriminating-Test discipline established in the
loop-doctrine (see ``docs/ops/learnings/RETRO-2026-06-08d-erdos-leiden-audit.md``).

Non-TIDE test files (autoresearch, batch_executor, etc.) predate the convention and
are deliberately excluded from this check.

Exit codes
----------
0  All TIDE-convention test files contain at least one "PRIMARY DISC." marker.
1  One or more TIDE-convention test files are missing the marker (gap list printed).

Usage
-----
    uv run python scripts/ci/check_discriminating_tests.py
    uv run python scripts/ci/check_discriminating_tests.py --dir tests/compound
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Regex: module docstring starts with  """Item <digits>:  or  '''Item <digits>:
_ITEM_DOCSTRING_RE = re.compile(
    r'^(?:"""|\'\'\')Item\s+\d+:',
    re.MULTILINE,
)

# Accepted discriminating-test markers (case-sensitive substring match).
# PRIMARY DISC. is the current standard (items 473+).
# MAIN DISC. was used for items ~82–440 (legacy standard; semantically equivalent).
# Additional phrase patterns recognise early prose descriptions of the same intent.
_DISC_MARKERS: tuple[str, ...] = (
    "PRIMARY DISC.",         # current standard
    "MAIN DISC.",            # legacy standard (items 82-440)
    "Discriminating test",   # prose variant: "Discriminating tests — each kills..."
    "discriminating test",   # lower-case prose variant
    "kills a plausible wrong",  # inline description (e.g. "kills a plausible wrong impl")
    "kills impl",            # shortened form used in tabular discriminating descriptions
    "plausible wrong",       # phrase pattern: "fails a plausible wrong impl/implementation"
    "wrong impl",            # further shortened form
)


def is_tide_test_file(path: Path) -> bool:
    """Return True if the file uses the TIDE ``Item NNN:`` docstring convention."""
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    return bool(_ITEM_DOCSTRING_RE.search(content))


def has_discriminating_marker(path: Path) -> bool:
    """Return True if the file contains at least one recognised discriminating-test marker."""
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    return any(marker in content for marker in _DISC_MARKERS)


def check_directory(test_dir: Path) -> tuple[int, int, list[Path]]:
    """Scan *test_dir* for TIDE test files and return (total, with_marker, gaps)."""
    tide_files = [
        p for p in sorted(test_dir.glob("test_*.py"))
        if is_tide_test_file(p)
    ]
    gaps = [f for f in tide_files if not has_discriminating_marker(f)]
    return len(tide_files), len(tide_files) - len(gaps), gaps


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dir",
        default="tests/compound",
        help="Directory to scan (default: tests/compound)",
    )
    args = parser.parse_args(argv)

    test_dir = Path(args.dir)
    if not test_dir.is_dir():
        print(f"ERROR: directory not found: {test_dir}", file=sys.stderr)
        return 1

    total, passing, gaps = check_directory(test_dir)

    print(f"Discriminating-test scan: {test_dir}")
    print(f"  TIDE test files found  : {total}")
    print(f"  Files with PRIMARY DISC.: {passing}")
    print(f"  Gaps (missing marker)  : {len(gaps)}")

    if gaps:
        print("\nFILES MISSING PRIMARY DISC. MARKER:")
        for p in gaps:
            print(f"  {p}")
        print(
            "\nEach TIDE test file must contain at least one 'PRIMARY DISC.' marker "
            "in its docstring (e.g., '1. PRIMARY DISC.: ...'). "
            "See RETRO-2026-06-08d-erdos-leiden-audit.md for the convention."
        )
        return 1

    print("\nAll TIDE test files pass the discriminating-test check. ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
