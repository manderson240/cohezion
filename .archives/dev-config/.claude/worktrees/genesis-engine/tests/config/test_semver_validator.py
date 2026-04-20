"""Tests for Semver CI Pipeline Validator (Story 7.1)."""

from __future__ import annotations

from cohezion.config.semver_validator import (
    BumpType,
    SemVer,
    SemverValidator,
)


class TestSemVer:
    def test_parse_basic(self):
        sv = SemVer.parse("1.2.3")
        assert sv is not None
        assert sv.major == 1 and sv.minor == 2 and sv.patch == 3

    def test_parse_with_v_prefix(self):
        sv = SemVer.parse("v1.0.0")
        assert sv is not None
        assert sv.major == 1

    def test_parse_prerelease(self):
        sv = SemVer.parse("1.0.0-alpha.1")
        assert sv is not None
        assert sv.pre == "alpha.1"

    def test_parse_invalid(self):
        assert SemVer.parse("not-a-version") is None

    def test_str(self):
        sv = SemVer(1, 2, 3)
        assert str(sv) == "1.2.3"

    def test_str_with_pre(self):
        sv = SemVer(1, 0, 0, pre="rc.1")
        assert str(sv) == "1.0.0-rc.1"


class TestSemverValidator:
    def test_detect_breaking_change(self):
        validator = SemverValidator()
        bump = validator.detect_bump_type(["feat!: breaking API change"])
        assert bump == BumpType.MAJOR

    def test_detect_feature(self):
        validator = SemverValidator()
        bump = validator.detect_bump_type(["feat: add new endpoint"])
        assert bump == BumpType.MINOR

    def test_detect_fix(self):
        validator = SemverValidator()
        bump = validator.detect_bump_type(["fix: resolve null check"])
        assert bump == BumpType.PATCH

    def test_detect_breaking_footer(self):
        validator = SemverValidator()
        bump = validator.detect_bump_type(["feat: add X\n\nBREAKING CHANGE: removes old API"])
        assert bump == BumpType.MAJOR

    def test_no_conventional_commits(self):
        validator = SemverValidator()
        bump = validator.detect_bump_type(["update readme", "misc cleanup"])
        assert bump == BumpType.NONE

    def test_valid_patch_bump(self):
        validator = SemverValidator()
        result = validator.validate("1.0.0", "1.0.1", ["fix: bug"])
        assert result.valid

    def test_valid_minor_bump(self):
        validator = SemverValidator()
        result = validator.validate("1.0.0", "1.1.0", ["feat: new feature"])
        assert result.valid

    def test_insufficient_bump_rejected(self):
        validator = SemverValidator()
        result = validator.validate("1.0.0", "1.0.1", ["feat: new feature"])
        assert not result.valid
        assert any("Insufficient" in e for e in result.errors)

    def test_no_bump_when_expected(self):
        validator = SemverValidator()
        result = validator.validate("1.0.0", "1.0.0", ["fix: something"])
        assert not result.valid

    def test_invalid_version_string(self):
        validator = SemverValidator()
        result = validator.validate("bad", "1.0.0", [])
        assert not result.valid

    def test_serialization(self):
        validator = SemverValidator()
        result = validator.validate("1.0.0", "1.1.0", ["feat: x"])
        d = result.to_dict()
        assert "valid" in d
        assert "expected_bump" in d
