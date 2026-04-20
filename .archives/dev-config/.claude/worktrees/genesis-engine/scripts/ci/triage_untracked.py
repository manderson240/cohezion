#!/usr/bin/env python3
"""
Triage Untracked Files

Categorizes untracked files and recommends disposition.
Part of Priority #2 from Party Mode Consensus.

Usage:
    uv run python scripts/ci/triage_untracked.py
    uv run python scripts/ci/triage_untracked.py --fix
"""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Category(Enum):
    """File category for triage."""

    GITIGNORE = "A"  # Should be in .gitignore
    TRACK = "B"  # Should be versioned
    DELETE = "C"  # Should be deleted
    REVIEW = "D"  # Needs human review


@dataclass
class TriageResult:
    """Result of triaging a file."""

    path: str
    category: Category
    reason: str
    action: str


# Known patterns for each category
GITIGNORE_PATTERNS = [
    # Build artifacts
    "__pycache__",
    ".pyc",
    ".pyo",
    ".pyd",
    ".ruff_cache",
    ".mypy_cache",
    ".pytest_cache",
    "*.egg-info",
    "dist",
    "build",
    # IDE
    ".vscode",
    ".idea",
    "*.swp",
    "*.swo",
    # Environment
    ".env",
    ".venv",
    "venv",
    "env",
    # Generated data
    "data/journeys",
    "data/surrealdb",
    "data/cache",
    "*.parquet",
    "*.jsonl",
    "*.pt",
    "*.pkl",
    "*.checkpoint",
    "*.model",
    "*.weights",
    # Logs
    "*.log",
    "logs/",
    # Temporary
    "*.tmp",
    "*.temp",
    # Test artifacts
    ".coverage",
    "htmlcov",
    ".tox",
    # Claude worktrees
    ".claude/worktrees",
    # Large files
    "node_modules",
    "*.zip",
]

TRACK_PATTERNS = [
    # Source code
    "src/",
    "tests/",
    "scripts/",
    # Config
    ".github/",
    "Makefile",
    "pyproject.toml",
    "ruff.toml",
    "mypy.ini",
    # Documentation
    "docs/",
    "README.md",
    "QUICKSTART.md",
    # Agent configs
    ".agent/",
    "_bmad/",
    # Important files
    "LICENSE",
    "CONSTITUTION.md",
]

DELETE_PATTERNS = [
    # Temporary/debug files
    "debug_",
    "test_run_",
    "old_",
    "backup_",
    # Generated output (can be regenerated)
    "ruff_out",
    "mypy_errors",
]


def categorize_file(path: str) -> TriageResult:
    """Categorize a single file."""
    path_lower = path.lower()

    # Check gitignore patterns
    for pattern in GITIGNORE_PATTERNS:
        if pattern in path_lower:
            return TriageResult(
                path=path,
                category=Category.GITIGNORE,
                reason=f"Matches gitignore pattern: {pattern}",
                action=f"Add '{pattern}' to .gitignore if not present",
            )

    # Check track patterns
    for pattern in TRACK_PATTERNS:
        if path.startswith(pattern):
            return TriageResult(
                path=path,
                category=Category.TRACK,
                reason=f"Should be versioned: {pattern}",
                action="git add {path}",
            )

    # Check delete patterns
    for pattern in DELETE_PATTERNS:
        if pattern in path_lower:
            return TriageResult(
                path=path,
                category=Category.DELETE,
                reason=f"Temporary/debug: {pattern}",
                action="rm {path}",
            )

    # Needs review
    return TriageResult(
        path=path,
        category=Category.REVIEW,
        reason="Unknown category - needs human review",
        action="Review and categorize manually",
    )


def get_untracked_files() -> list[str]:
    """Get list of untracked files from git."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent,
    )

    untracked = []
    for line in result.stdout.splitlines():
        if line.startswith("??"):
            untracked.append(line[3:])

    return untracked


def triage_all() -> dict[Category, list[TriageResult]]:
    """Triage all untracked files."""
    untracked = get_untracked_files()
    results: dict[Category, list[TriageResult]] = {cat: [] for cat in Category}

    for path in untracked:
        result = categorize_file(path)
        results[result.category].append(result)

    return results


def print_report(results: dict[Category, list[TriageResult]]) -> None:
    """Print triage report."""
    total = sum(len(r) for r in results.values())

    print("\n" + "=" * 60)
    print("UNTRACKED FILES TRIAGE REPORT")
    print("=" * 60)
    print(f"\nTotal untracked: {total}")

    print("\n" + "-" * 60)
    print("Category A: Should be in .gitignore")
    print("-" * 60)
    for r in results[Category.GITIGNORE][:10]:
        print(f"  {r.path}")
        print(f"    → {r.reason}")
    if len(results[Category.GITIGNORE]) > 10:
        print(f"  ... and {len(results[Category.GITIGNORE]) - 10} more")

    print("\n" + "-" * 60)
    print("Category B: Should be versioned")
    print("-" * 60)
    for r in results[Category.TRACK][:10]:
        print(f"  {r.path}")
        print(f"    → {r.action}")
    if len(results[Category.TRACK]) > 10:
        print(f"  ... and {len(results[Category.TRACK]) - 10} more")

    print("\n" + "-" * 60)
    print("Category C: Should be deleted")
    print("-" * 60)
    for r in results[Category.DELETE][:10]:
        print(f"  {r.path}")
        print(f"    → {r.reason}")
    if len(results[Category.DELETE]) > 10:
        print(f"  ... and {len(results[Category.DELETE]) - 10} more")

    print("\n" + "-" * 60)
    print("Category D: Needs human review")
    print("-" * 60)
    for r in results[Category.REVIEW][:10]:
        print(f"  {r.path}")
        print(f"    → {r.reason}")
    if len(results[Category.REVIEW]) > 10:
        print(f"  ... and {len(results[Category.REVIEW]) - 10} more")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  A (GitIgnore): {len(results[Category.GITIGNORE])}")
    print(f"  B (Track):     {len(results[Category.TRACK])}")
    print(f"  C (Delete):    {len(results[Category.DELETE])}")
    print(f"  D (Review):    {len(results[Category.REVIEW])}")

    # Priority recommendations
    print("\n" + "=" * 60)
    print("PRIORITY ACTIONS")
    print("=" * 60)

    if results[Category.TRACK]:
        print(f"\n1. TRACK {len(results[Category.TRACK])} files:")
        print("   git add [category B files]")

    if results[Category.GITIGNORE]:
        print(f"\n2. UPDATE .gitignore ({len(results[Category.GITIGNORE])} files)")

    if results[Category.DELETE]:
        print(f"\n3. DELETE {len(results[Category.DELETE])} temp files:")
        print("   rm [category C files]")

    if results[Category.REVIEW]:
        print(f"\n4. REVIEW {len(results[Category.REVIEW])} files manually")


def apply_fixes(results: dict[Category, list[TriageResult]], dry_run: bool = True) -> None:
    """Apply triage fixes."""
    if dry_run:
        print("\n🔧 DRY RUN - No changes will be made")

    # Track category B files
    track_files = [r.path for r in results[Category.TRACK]]
    if track_files and not dry_run:
        project_root = Path(__file__).parent.parent.parent
        for f in track_files[:50]:  # Limit to 50 at a time
            path = project_root / f
            if path.exists():
                subprocess.run(["git", "add", str(path)], cwd=project_root)
        print(f"Staged {min(50, len(track_files))} files for tracking")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Triage untracked files")
    parser.add_argument("--fix", action="store_true", help="Apply fixes (track category B)")
    parser.add_argument(
        "--dry-run", action="store_true", default=True, help="Show what would be done"
    )
    parser.add_argument("--output", choices=["text", "json"], default="text", help="Output format")
    args = parser.parse_args()

    results = triage_all()

    if args.output == "json":
        import json

        output = {
            cat.value: [{"path": r.path, "reason": r.reason} for r in results[cat]]
            for cat in Category
        }
        print(json.dumps(output, indent=2))
    else:
        print_report(results)

    if args.fix:
        apply_fixes(results, dry_run=args.dry_run)

    # Return count of files needing attention
    return len(results[Category.TRACK]) + len(results[Category.REVIEW])


if __name__ == "__main__":
    raise SystemExit(main())
