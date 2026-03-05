#!/usr/bin/env python3
"""CI: Version governance using Epic 7 release modules.

Validates commits, changelog, and version consistency using the
Python modules built in Epic 7 instead of shell-based parsing.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from cohezion.release.bump_validator import BumpType, BumpValidator
from cohezion.release.changelog_validator import ChangelogValidator
from cohezion.release.version_detector import VersionDetector


# All valid conventional commit types (superset of bump-triggering types)
_CONVENTIONAL_PATTERN = re.compile(
    r"^(feat|fix|perf|refactor|test|docs|build|ci|chore|revert|style)"
    r"(\([^)]*\))?!?\s*:\s*.+",
    re.DOTALL,
)


def get_pr_commits(base_sha: str | None = None) -> list[str]:
    """Get commit messages for the current PR or since last tag."""
    if base_sha:
        cmd = ["git", "log", f"{base_sha}..HEAD", "--format=%s"]
    else:
        # Fall back to commits since last tag
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
        bump = BumpValidator.classify_commit(commit)
        if bump > max_bump:
            max_bump = bump
        # Flag truly non-conventional commits (skip merge/revert)
        if not _CONVENTIONAL_PATTERN.match(commit):
            if not commit.startswith("Merge ") and not commit.startswith("Revert "):
                issues.append(f"Non-conventional commit: {commit!r}")

    return max_bump, issues


def validate_changelog(bump_type: BumpType, changelog_path: Path) -> list[str]:
    """Validate changelog sections match bump type."""
    issues: list[str] = []

    if not changelog_path.exists():
        if bump_type != BumpType.NONE:
            issues.append("No CHANGELOG.md found — required for version bumps")
        return issues

    result = ChangelogValidator.validate_file(changelog_path, bump_type)
    if not result.valid:
        issues.append(f"Changelog issue: {result.guidance}")
        if result.missing_sections:
            issues.append(f"Missing sections: {', '.join(result.missing_sections)}")

    return issues


def validate_version_consistency(project_root: Path) -> list[str]:
    """Check version in pyproject.toml matches git tags."""
    issues: list[str] = []
    detector = VersionDetector()

    pyproject = project_root / "pyproject.toml"
    if not pyproject.exists():
        issues.append("No pyproject.toml found")
        return issues

    try:
        pyproject_version = detector.detect_from_pyproject(pyproject)
    except ValueError as e:
        issues.append(f"Cannot parse pyproject.toml version: {e}")
        return issues

    tag_version = detector.detect_latest()
    if tag_version and pyproject_version.as_tuple() < tag_version.as_tuple():
        issues.append(f"pyproject.toml version ({pyproject_version}) is behind latest tag ({tag_version})")

    return issues


def main() -> int:
    """Run version governance checks."""
    project_root = Path.cwd()
    base_sha = sys.argv[1] if len(sys.argv) > 1 else None

    print("=== Version Governance Check ===\n")

    # 1. Get and classify commits
    commits = get_pr_commits(base_sha)
    if not commits:
        print("No commits to analyze — skipping governance checks.")
        return 0

    print(f"Analyzing {len(commits)} commit(s)...")
    bump_type, commit_issues = validate_commits(commits)
    print(f"Detected bump type: {bump_type.name}")

    # 2. Validate changelog
    changelog_issues = validate_changelog(bump_type, project_root / "CHANGELOG.md")

    # 3. Validate version consistency
    version_issues = validate_version_consistency(project_root)

    # 4. Report
    all_issues = commit_issues + changelog_issues + version_issues

    if commit_issues:
        print(f"\nCommit issues ({len(commit_issues)}):")
        for issue in commit_issues:
            print(f"  ⚠️  {issue}")

    if changelog_issues:
        print(f"\nChangelog issues ({len(changelog_issues)}):")
        for issue in changelog_issues:
            print(f"  ⚠️  {issue}")

    if version_issues:
        print(f"\nVersion issues ({len(version_issues)}):")
        for issue in version_issues:
            print(f"  ⚠️  {issue}")

    # Output for GitHub Actions
    output = {
        "bump_type": bump_type.name,
        "commit_count": len(commits),
        "issues": all_issues,
        "passed": len(changelog_issues) == 0 and len(version_issues) == 0,
    }
    print(f"\n{json.dumps(output, indent=2)}")

    # Fail on changelog or version issues (commit warnings are non-blocking)
    if changelog_issues or version_issues:
        print("\n❌ Version governance check FAILED")
        return 1

    if commit_issues:
        print(f"\n⚠️  Version governance PASSED with {len(commit_issues)} commit warning(s)")
    else:
        print("\n✅ Version governance check PASSED")

    return 0


if __name__ == "__main__":
    sys.exit(main())
