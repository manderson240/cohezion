#!/usr/bin/env python3
"""Claude Code PostToolUse hook: warn when production code is written without a test.

Protocol:
  - Reads JSON from stdin (Claude Code hook format)
  - Exit 0 always (non-blocking warning only)
  - Prints TDD reminder to stdout when production Python file is written
    without a corresponding test file being modified in the same turn.
"""
import json
import sys
from pathlib import Path

# File extensions that trigger the check
PRODUCTION_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx"}
# Patterns indicating a test file (won't trigger warning)
TEST_PATTERNS = ("test_", "_test.", ".test.", ".spec.")


def is_test_file(path: Path) -> bool:
    name = path.name
    return any(pat in name for pat in TEST_PATTERNS) or "/tests/" in str(path)


def main() -> int:
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_name = data.get("tool_name", "")
    if tool_name not in ("Write", "Edit", "MultiEdit"):
        return 0

    tool_input = data.get("tool_input", {})
    file_path_str = tool_input.get("file_path") or tool_input.get("path")
    if not file_path_str:
        return 0

    file_path = Path(file_path_str)

    # Only check production code files
    if file_path.suffix not in PRODUCTION_EXTENSIONS:
        return 0

    # If this IS a test file, no warning needed
    if is_test_file(file_path):
        return 0

    # Production file written - remind about TDD
    print(
        f"📋 TDD REMINDER: You wrote production code in {file_path.name}. "
        "Ensure a failing test exists FIRST (or was written in this session). "
        "See tdd-enforcement.md rules.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
