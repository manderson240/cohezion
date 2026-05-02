#!/usr/bin/env python3
"""Generate executable agents from PRIME skill definitions.

Usage::

    uv run python scripts/generate_agents.py [--count 5] [--skill NAME]
    uv run python scripts/generate_agents.py --list
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cohezion.agents.factory import AgentFactory


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for agent generation."""
    parser = argparse.ArgumentParser(description="Generate executable agents from PRIME skills")
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of top skills to generate agents for",
    )
    parser.add_argument(
        "--skill",
        type=str,
        default=None,
        help="Generate agent for a specific skill name",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available skills",
    )
    args = parser.parse_args(argv)

    factory = AgentFactory()

    if args.list:
        skills = factory.list_available_skills()
        print(f"Available PRIME skills ({len(skills)}):")
        for name in skills:
            print(f"  - {name}")
        return

    if args.skill:
        from cohezion.core.config_templates import ConfigTemplateManager

        manager = ConfigTemplateManager(engine=factory._engine)
        try:
            result = manager.generate_executable_and_register(args.skill)
            print(f"Generated: {args.skill} -> {result['agent']}")
        except KeyError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        generated = factory.generate_top_skills(count=args.count)
        print(f"Generated {len(generated)} executable agents:")
        for name in generated:
            print(f"  - {name}")


if __name__ == "__main__":
    main()
