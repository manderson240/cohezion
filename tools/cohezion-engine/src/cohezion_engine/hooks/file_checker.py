#!/usr/bin/env python3
"""Claude Code PostToolUse hook: enforce file size limits.

Protocol:
  - Reads JSON from stdin (Claude Code hook format)
  - Exit 0: pass (file is OK or not a file tool)
  - Exit 2: block with message (file exceeds hard limit)
  - Prints warnings to stdout
"""
import json
import sys
from pathlib import Path

WARN_THRESHOLD = 300
BLOCK_THRESHOLD = 500


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

    # Test files are exempt from size limits
    if file_path.name.startswith("test_") or "/tests/" in str(file_path):
        return 0

    if not file_path.exists():
        return 0

    try:
        line_count = len(file_path.read_text().splitlines())
    except OSError:
        return 0

    if line_count > BLOCK_THRESHOLD:
        print(
            f"🚫 BLOCKED: {file_path.name} has {line_count} lines "
            f"(hard limit: {BLOCK_THRESHOLD}). Split into focused modules before proceeding.",
            flush=True,
        )
        return 2

    if line_count > WARN_THRESHOLD:
        print(
            f"⚠ WARNING: {file_path.name} has {line_count} lines "
            f"(target: {WARN_THRESHOLD}). Consider splitting soon.",
            flush=True,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
