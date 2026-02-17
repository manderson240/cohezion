#!/usr/bin/env python3
"""Validate that a PR title follows conventional commit format.

Since GitHub squash-merge uses the PR title as the commit message,
the PR title must follow conventional commit format.

Usage:
    python scripts/ci/check_pr_title.py "feat: add auth"

Exit codes:
    0 - Title is valid
    1 - Title is invalid
"""

import re
import sys


TYPES = (
    "feat",
    "fix",
    "refactor",
    "test",
    "docs",
    "chore",
    "perf",
    "ci",
    "build",
    "style",
    "revert",
)

_TYPES_PATTERN = "|".join(re.escape(t) for t in TYPES)
PATTERN = re.compile(
    rf"^(?:{_TYPES_PATTERN})"
    r"(\([^)]+\))?"
    r"!?"
    r": "
    r".+$"
)


def validate(title: str) -> bool:
    """Return True if title is a valid conventional commit message."""
    return bool(PATTERN.match(title))


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: check_pr_title.py <title>", file=sys.stderr)
        return 1

    title = sys.argv[1]
    if validate(title):
        print(f"✓ PR title is valid: {title!r}")
        return 0
    else:
        print(
            f"✗ PR title does not follow conventional commit format: {title!r}\n"
            f"  Expected: <type>[scope][!]: <description>\n"
            f"  Types: {', '.join(TYPES)}\n"
            "  Examples: 'feat: add auth', 'fix(api): handle null',"
            " 'refactor!: break API'",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
