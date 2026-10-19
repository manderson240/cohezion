#!/usr/bin/env python3
"""Cohezion High-Speed Pyrefly Type Checking Runner (Google / Meta Rust Engine).

Runs parallel type checking over the codebase with Pyrefly, emitting actionable
Rust-style diagnostic reports with suggestions.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cohezion.type_checking.pyrefly_adapter import PyreflyAdapter


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Pyrefly type checking on Cohezion source tree."
    )
    parser.add_argument(
        "paths", nargs="*", default=["src", "tests"], help="Paths to check (default: src tests)"
    )
    parser.add_argument("-j", "--threads", type=int, default=0, help="Number of threads (0=auto)")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    adapter = PyreflyAdapter()
    if not adapter.is_available():
        print(
            "✗ Pyrefly is not installed or not in PATH. Run `uv pip install pyrefly`.",
            file=sys.stderr,
        )
        return 1

    target_paths = [Path(p) for p in args.paths]
    print(f"== Running Pyrefly (Rust Engine) on {len(target_paths)} target path(s)... ==")
    result = adapter.check_files(target_paths, threads=args.threads)

    if result.passed:
        print(
            f"✓ Pyrefly PASSED in {result.duration_ms:.2f}ms — 0 errors, {result.warnings_count} warnings."
        )
        return 0

    print(
        f"✗ Pyrefly found {result.errors_count} error(s) and {result.warnings_count} warning(s) in {result.duration_ms:.2f}ms:\n"
    )
    for d in result.diagnostics:
        print(f"  --> {d.file}:{d.line}:{d.column} [{d.error_code}] ({d.severity})")
        print(f"      {d.message}")
        if d.suggestion:
            print(f"      💡 Hint: {d.suggestion}")
        print()

    return 1 if result.errors_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
