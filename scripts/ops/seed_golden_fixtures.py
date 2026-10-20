#!/usr/bin/env python3
"""Seed a skill's checked-in golden fixtures into SurrealDB ``golden_fixture`` (human-run).

The FAPO R3 regression gate (``PromptVersionRegistry.regression_check``) reads fixtures
only from the live DB. This copies ``src/cohezion/compound/golden_fixtures/<skill>.json``
there through the same injection-safe writer the gate's bootstrap uses.

    PYTHONPATH=src python3 scripts/ops/seed_golden_fixtures.py research-actioner          # preview
    PYTHONPATH=src python3 scripts/ops/seed_golden_fixtures.py research-actioner --apply  # write

Refuses when the skill already has rows: SkillRefiner never re-authors fixtures once any
exist, and a second seed would duplicate every case.
"""

from __future__ import annotations

import argparse
import sys

from cohezion.compound.prompt_version_registry import (
    PromptVersionRegistry,
    load_golden_fixture_file,
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("skill_name")
    ap.add_argument("--apply", action="store_true", help="write rows (default: preview)")
    args = ap.parse_args(argv)

    fixtures = load_golden_fixture_file(args.skill_name)
    if not fixtures:
        print(f"no checked-in fixtures for {args.skill_name}")
        return 1
    reg = PromptVersionRegistry()
    try:
        existing = reg._load_behavioral_fixtures(args.skill_name)
    except Exception as exc:  # cannot tell whether rows exist: do not risk duplicates
        print(f"cannot read golden_fixture ({exc}); nothing written")
        return 2
    if existing:
        print(f"{args.skill_name} already has {len(existing)} golden_fixture rows; nothing written")
        return 0
    critical = sum(1 for f in fixtures if f["critical"])
    print(f"{args.skill_name}: {len(fixtures)} fixtures ({critical} critical)")
    if not args.apply:
        print("preview only; re-run with --apply to write")
        return 0
    written = sum(reg._write_fixture(args.skill_name, f) for f in fixtures)
    print(f"wrote {written}/{len(fixtures)}")
    return 0 if written == len(fixtures) else 3


if __name__ == "__main__":
    sys.exit(main())
