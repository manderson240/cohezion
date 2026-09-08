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


_CHANGELOG_CLAIM_PATTERN = re.compile(r"`([\w./-]+\.\w+|[\w]+(?:\.[\w]+)+)`")


def validate_changelog_claims(changelog_path: Path, project_root: Path) -> list[str]:
    """Verify file/module paths claimed under [Unreleased]'s Added/Changed actually exist.

    Catches phantom entries: a Changelog claiming a module/file was added when it
    was never actually committed. Scoped to Added/Changed only — a Removed entry's
    whole point is describing something that no longer (or never did) exist, and
    Fixed/Note entries aren't claims of new capability, so neither should be flagged.
    """
    issues: list[str] = []
    if not changelog_path.exists():
        return issues

    content = changelog_path.read_text()
    unreleased_match = re.search(r"## \[Unreleased\](.*?)(?=\n## \[|\Z)", content, re.DOTALL)
    if not unreleased_match:
        return issues

    claim_text = "\n".join(
        section_match.group(1)
        for section_match in re.finditer(
            r"### (?:Added|Changed)\n(.*?)(?=\n### |\Z)", unreleased_match.group(1), re.DOTALL
        )
    )

    for candidate in _CHANGELOG_CLAIM_PATTERN.findall(claim_text):
        if "/" in candidate or candidate.endswith(
            (".py", ".ts", ".tsx", ".sh", ".yml", ".yaml", ".md")
        ):
            if not (project_root / candidate).exists():
                issues.append(f"CHANGELOG claims '{candidate}' but no such file exists in the repo")
        elif candidate.startswith("cohezion."):
            rel = candidate.replace(".", "/")
            if (
                not (project_root / "src" / f"{rel}.py").exists()
                and not (project_root / "src" / rel / "__init__.py").exists()
            ):
                issues.append(
                    f"CHANGELOG claims module '{candidate}' but no such module exists in the repo"
                )

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


def _parse_semver(version: str) -> tuple[int, int, int] | None:
    """MAJOR.MINOR.PATCH as ints, ignoring any pre-release/build suffix."""
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)", version.strip())
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def get_version_at_ref(ref: str) -> str | None:
    """pyproject.toml version as of a git ref (the PR base), or None if unreadable."""
    try:
        result = subprocess.run(
            ["git", "show", f"{ref}:pyproject.toml"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        m = re.match(r'^version\s*=\s*"([^"]+)"', line.strip())
        if m:
            return m.group(1)
    return None


def actual_bump(base: str, head: str) -> BumpType | None:
    """The bump the version numbers actually express between two versions."""
    b, h = _parse_semver(base), _parse_semver(head)
    if b is None or h is None:
        return None
    if h < b:
        return None  # a decrease is never a valid bump; caller reports it
    if h[0] != b[0]:
        return BumpType.MAJOR
    if h[1] != b[1]:
        return BumpType.MINOR
    if h[2] != b[2]:
        return BumpType.PATCH
    return BumpType.NONE


def validate_version_bump(
    bump_type: BumpType, base_sha: str | None, head_version: str | None
) -> list[str]:
    """The version must actually BE bumped, by at least what the commits imply.

    Without this the gate was named "Semver Check" while checking no semver: it classified
    the commits into a bump type and then only verified that pyproject.toml had a *readable*
    version, so a PR full of `feat:` commits could land with the version untouched.

    Fail-OPEN when the comparison is impossible (no base SHA, unreadable base pyproject,
    unparseable version) — a CI checkout quirk must not block a legitimate PR. It fails
    CLOSED only when both versions are known and the bump is genuinely insufficient.
    """
    if bump_type == BumpType.NONE or not base_sha or not head_version:
        return []
    base_version = get_version_at_ref(base_sha)
    if base_version is None:
        return []  # base pyproject unreadable (shallow clone / new file) — cannot judge
    if base_version == head_version:
        return [
            f"Version not bumped: still {head_version}, but commits imply a "
            f"{bump_type.name} bump. Bump [project].version in pyproject.toml "
            f"and add a CHANGELOG entry."
        ]
    got = actual_bump(base_version, head_version)
    if got is None:
        return [f"Version went backwards or is unparseable: {base_version} -> {head_version}"]
    if got < bump_type:
        return [
            f"Version bump too small: {base_version} -> {head_version} is a {got.name} "
            f"bump, but commits imply {bump_type.name}."
        ]
    return []


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
    changelog_issues += validate_changelog_claims(project_root / "CHANGELOG.md", project_root)

    version = get_pyproject_version(project_root)
    version_issues: list[str] = []
    if version:
        print(f"Current version: {version}")
        # Validate that if MINOR or MAJOR bump detected, pyproject.toml version matches or exceeds
        latest_tag = None
        try:
            r = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                capture_output=True,
                text=True,
                check=True,
            )
            latest_tag = r.stdout.strip().lstrip("v")
        except Exception:
            pass

        if latest_tag and bump_type != BumpType.NONE:
            if latest_tag == version and bump_type >= BumpType.MINOR:
                version_issues.append(
                    f"pyproject.toml version '{version}' equals git tag '{latest_tag}' but a {bump_type.name} bump is required."
                )
    else:
        version_issues.append("Cannot read version from pyproject.toml")
    version_issues += validate_version_bump(bump_type, base_sha, version)

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
