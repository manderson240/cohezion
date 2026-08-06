"""Unit tests for scripts/ci/version_governance.py's validate_changelog_claims().

Added after discovering a real phantom CHANGELOG entry (a `cohezion.release`
module claimed as Added that was never actually committed on any branch, per
`git log --all`). Uses tmp_path for isolation rather than the repo's own
CHANGELOG.md / src tree.
"""

from __future__ import annotations

import sys
from pathlib import Path


_SCRIPTS_CI_DIR = Path(__file__).resolve().parents[2] / "scripts" / "ci"
if str(_SCRIPTS_CI_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_CI_DIR))

from version_governance import (
    BumpType,
    actual_bump,
    validate_changelog_claims,
    validate_version_bump,
)


# ── the version actually gets BUMPED (2026-08-01) ────────────────────────────────
# The workflow is named "Semver Check" but checked no semver: it classified the commits
# into a bump type, then only verified pyproject.toml had a *readable* version. A PR of
# `feat:` commits could land with the version untouched — verified against this repo's own
# branch, which passed with "issues": [] after 5 fix commits and no bump.


def test_no_bump_is_rejected_when_commits_imply_one(monkeypatch) -> None:
    """The original defect: same version at base and head must FAIL."""
    monkeypatch.setattr("version_governance.get_version_at_ref", lambda ref: "1.2.0")
    issues = validate_version_bump(BumpType.PATCH, "basesha", "1.2.0")
    assert issues and "not bumped" in issues[0]


def test_bump_smaller_than_commits_imply_is_rejected(monkeypatch) -> None:
    """A `feat:` PR (MINOR) that only bumps the patch digit must FAIL."""
    monkeypatch.setattr("version_governance.get_version_at_ref", lambda ref: "1.2.0")
    issues = validate_version_bump(BumpType.MINOR, "basesha", "1.2.1")
    assert issues and "too small" in issues[0]


def test_sufficient_bump_passes(monkeypatch) -> None:
    monkeypatch.setattr("version_governance.get_version_at_ref", lambda ref: "1.2.0")
    assert validate_version_bump(BumpType.PATCH, "basesha", "1.2.1") == []
    # Over-bumping is fine: the commit type is a MINIMUM, not an equality.
    assert validate_version_bump(BumpType.PATCH, "basesha", "2.0.0") == []


def test_backwards_version_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr("version_governance.get_version_at_ref", lambda ref: "1.2.0")
    issues = validate_version_bump(BumpType.PATCH, "basesha", "1.1.9")
    assert issues and "backwards" in issues[0]


def test_fails_open_when_the_comparison_is_impossible(monkeypatch) -> None:
    """A CI checkout quirk must never block a legitimate PR — only a KNOWN-bad bump fails."""
    monkeypatch.setattr("version_governance.get_version_at_ref", lambda ref: None)
    assert validate_version_bump(BumpType.PATCH, "basesha", "1.2.1") == []  # base unreadable
    assert validate_version_bump(BumpType.PATCH, None, "1.2.1") == []  # no base SHA
    assert validate_version_bump(BumpType.NONE, "basesha", "1.2.0") == []  # nothing implied


def test_actual_bump_classifies_each_digit() -> None:
    assert actual_bump("1.2.0", "2.0.0") is BumpType.MAJOR
    assert actual_bump("1.2.0", "1.3.0") is BumpType.MINOR
    assert actual_bump("1.2.0", "1.2.1") is BumpType.PATCH
    assert actual_bump("1.2.0", "1.2.0") is BumpType.NONE
    assert actual_bump("1.2.0", "1.1.0") is None  # decrease
    assert actual_bump("1.2.0", "not-a-version") is None


def test_flags_phantom_module_in_added_section(tmp_path: Path) -> None:
    """A backtick-quoted module in ### Added that doesn't exist must be flagged."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "## [Unreleased]\n\n### Added\n"
        "- Semantic version detection module (`cohezion.release`) with git tag parsing\n"
    )
    issues = validate_changelog_claims(changelog, tmp_path)
    assert any("cohezion.release" in issue for issue in issues)


def test_does_not_flag_real_existing_module(tmp_path: Path) -> None:
    """A claim about a module that actually exists on disk must not be flagged."""
    (tmp_path / "src" / "cohezion").mkdir(parents=True)
    (tmp_path / "src" / "cohezion" / "release.py").write_text("# real module\n")
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "## [Unreleased]\n\n### Added\n- Real module (`cohezion.release`) landed\n"
    )
    issues = validate_changelog_claims(changelog, tmp_path)
    assert issues == []


def test_does_not_flag_removed_section_mentions(tmp_path: Path) -> None:
    """A Removed entry describing something that never existed is not a phantom
    claim -- it's explicitly saying the thing doesn't exist. Must not be flagged."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "## [Unreleased]\n\n### Removed\n"
        "- Corrected a previous claim about `cohezion.release` -- it never existed\n"
    )
    issues = validate_changelog_claims(changelog, tmp_path)
    assert issues == []


def test_flags_phantom_file_path_not_just_dotted_module(tmp_path: Path) -> None:
    """A backtick-quoted file path (not dotted-module notation) that doesn't
    exist should also be flagged."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "## [Unreleased]\n\n### Added\n- New script `scripts/ci/does_not_exist.sh`\n"
    )
    issues = validate_changelog_claims(changelog, tmp_path)
    assert any("does_not_exist.sh" in issue for issue in issues)


def test_only_scans_unreleased_section(tmp_path: Path) -> None:
    """A phantom claim under an already-released version section is historical
    and out of scope -- only [Unreleased] claims are actionable pre-release."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "## [Unreleased]\n\n### Added\n- Nothing new\n\n"
        "## [1.0.0] - 2026-01-01\n\n### Added\n"
        "- Old phantom claim (`cohezion.nonexistent`)\n"
    )
    issues = validate_changelog_claims(changelog, tmp_path)
    assert issues == []


def test_missing_changelog_returns_no_issues(tmp_path: Path) -> None:
    """No CHANGELOG.md at all is a separate concern (validate_changelog handles
    that) -- this function should just no-op rather than error."""
    issues = validate_changelog_claims(tmp_path / "CHANGELOG.md", tmp_path)
    assert issues == []
