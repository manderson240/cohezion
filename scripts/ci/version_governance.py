#!/usr/bin/env python3
"""CI: Version governance for conventional commits and changelog.

Validates commit messages follow conventional commit format and
checks changelog/version consistency. Self-contained (no internal
module dependencies) for CI reliability.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from enum import IntEnum
from pathlib import Path


class BumpType(IntEnum):
    NONE = 0
    PATCH = 1
    MINOR = 2
    MAJOR = 3


# All valid conventional commit types
_CONVENTIONAL_PATTERN = re.compile(
    r"^(feat|fix|perf|refactor|test|docs|build|ci|chore|revert|style)"
    r"(\([^)]*\))?!?\s*:\s*.+",
    re.DOTALL,
)

# Bump classification
_BUMP_RULES: list[tuple[re.Pattern[str], BumpType]] = [
    (re.compile(r"^.*!:\s"), BumpType.MAJOR),  # Breaking change (!)
    (re.compile(r"BREAKING CHANGE", re.IGNORECASE), BumpType.MAJOR),
    (re.compile(r"^feat(\(|:)"), BumpType.MINOR),
    (re.compile(r"^fix(\(|:)"), BumpType.PATCH),
    (re.compile(r"^perf(\(|:)"), BumpType.PATCH),
]


def classify_commit(message: str) -> BumpType:
    """Classify a commit message into a bump type."""
    for pattern, bump in _BUMP_RULES:
        if pattern.search(message):
            return bump
    return BumpType.NONE


def get_pr_commits(base_sha: str | None = None) -> list[str]:
    """Get commit messages for the current PR or since last tag."""
    if base_sha:
        cmd = ["git", "log", f"{base_sha}..HEAD", "--format=%s"]
    else:
        cmd = ["git", "log", "--format=%s"]
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                tag = result.stdout.strip()
                cmd = ["git", "log", f"{tag}..HEAD", "--format=%s"]
        except subprocess.TimeoutExpired:
            pass

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def validate_commits(commits: list[str]) -> tuple[BumpType, list[str]]:
    """Classify all commits and return max bump type + any issues."""
    issues: list[str] = []
    max_bump = BumpType.NONE

    for commit in commits:
        bump = classify_commit(commit)
        if bump > max_bump:
            max_bump = bump
        if not _CONVENTIONAL_PATTERN.match(commit):
            if not commit.startswith("Merge ") and not commit.startswith("Revert "):
                issues.append(f"Non-conventional commit: {commit!r}")

    return max_bump, issues


def validate_changelog(bump_type: BumpType, changelog_path: Path) -> list[str]:
    """Validate changelog exists for version bumps."""
    issues: list[str] = []

    if not changelog_path.exists():
        if bump_type != BumpType.NONE:
            issues.append("No CHANGELOG.md found - required for version bumps")
        return issues

    content = changelog_path.read_text()
    if (
        bump_type >= BumpType.MINOR
        and "## [Unreleased]" not in content
        and "## Unreleased" not in content
    ):
        issues.append("CHANGELOG.md missing [Unreleased] section for feature/breaking change")

    return issues


def get_pyproject_version(project_root: Path) -> str | None:
    """Extract version from pyproject.toml."""
    pyproject = project_root / "pyproject.toml"
    if not pyproject.exists():
        return None
    for line in pyproject.read_text().splitlines():
        m = re.match(r'^version\s*=\s*"([^"]+)"', line.strip())
        if m:
            return m.group(1)
    return None


def main() -> int:
    """Run version governance checks."""
    project_root = Path.cwd()
    base_sha = sys.argv[1] if len(sys.argv) > 1 else None

    print("=== Version Governance Check ===\n")

    commits = get_pr_commits(base_sha)
    if not commits:
        print("No commits to analyze - skipping governance checks.")
        return 0

    print(f"Analyzing {len(commits)} commit(s)...")
    bump_type, commit_issues = validate_commits(commits)
    print(f"Detected bump type: {bump_type.name}")

    changelog_issues = validate_changelog(bump_type, project_root / "CHANGELOG.md")

    version = get_pyproject_version(project_root)
    version_issues: list[str] = []
    if version:
        print(f"Current version: {version}")
    else:
        version_issues.append("Cannot read version from pyproject.toml")

    all_issues = commit_issues + changelog_issues + version_issues

    if commit_issues:
        print(f"\nCommit issues ({len(commit_issues)}):")
        for issue in commit_issues:
            print(f"  Warning: {issue}")

    if changelog_issues:
        print(f"\nChangelog issues ({len(changelog_issues)}):")
        for issue in changelog_issues:
            print(f"  Warning: {issue}")

    if version_issues:
        print(f"\nVersion issues ({len(version_issues)}):")
        for issue in version_issues:
            print(f"  Warning: {issue}")

    output = {
        "bump_type": bump_type.name,
        "commit_count": len(commits),
        "issues": all_issues,
        "passed": len(changelog_issues) == 0 and len(version_issues) == 0,
    }
    print(f"\n{json.dumps(output, indent=2)}")

    if changelog_issues or version_issues:
        print("\nVersion governance check FAILED")
        return 1

    if commit_issues:
        print(f"\nVersion governance PASSED with {len(commit_issues)} commit warning(s)")
    else:
        print("\nVersion governance check PASSED")

    return 0


if __name__ == "__main__":
    sys.exit(main())
