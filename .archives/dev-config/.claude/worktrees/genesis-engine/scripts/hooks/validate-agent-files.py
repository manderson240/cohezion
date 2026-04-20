#!/usr/bin/env python3
"""Pre-commit hook: validate Claude agent file frontmatter.

Usage:
    # Called by pre-commit with changed filenames:
    python scripts/hooks/validate-agent-files.py .claude/agents/foo.md

    # Validate all agent files manually:
    python scripts/hooks/validate-agent-files.py --all
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    try:
        from cohezion.validation.agent_schema import (
            AgentFileValidationError,
            validate_agent_file,
            validate_all_agent_files,
        )
    except ImportError:
        print("WARNING: cohezion not importable, skipping agent file validation")
        return 0

    if "--all" in sys.argv:
        try:
            results = validate_all_agent_files()
            print(f"✓ {len(results)} agent files validated successfully")
            return 0
        except AgentFileValidationError as exc:
            print(f"✗ Agent file validation failed:\n{exc}", file=sys.stderr)
            return 1

    files = [f for f in sys.argv[1:] if f.endswith(".md")]
    if not files:
        return 0

    errors: list[str] = []
    for filepath in files:
        path = Path(filepath)
        if not path.exists():
            continue
        try:
            result = validate_agent_file(path)
            print(f"✓ {path.name}: {result.name}")
        except AgentFileValidationError as exc:
            errors.append(str(exc))
            print(f"✗ {path.name}: validation failed", file=sys.stderr)

    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
