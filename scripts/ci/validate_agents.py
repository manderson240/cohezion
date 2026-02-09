#!/usr/bin/env python3
"""CI: Validate all Claude Code agent definition files."""

from __future__ import annotations

import sys

from cohezion.validation.agent_schema import (
    AgentFileValidationError,
    validate_all_agent_files,
)


def main() -> int:
    """Validate agent files, return 0 on success, 1 on failure."""
    try:
        agents = validate_all_agent_files()
    except AgentFileValidationError as exc:
        print("FAIL: Agent validation errors:")
        if exc.path:
            print(f"  File: {exc.path}")
        for err in exc.errors:
            print(f"  - {err}")
        return 1

    print(f"OK: {len(agents)} agent files validated successfully")
    for agent in agents:
        print(f"  - {agent.name}: {agent.description[:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
