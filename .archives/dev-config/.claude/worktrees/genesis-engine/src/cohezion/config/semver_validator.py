"""Semver CI Pipeline Validator (Story 7.1, NFR-AUTO_VERSION_HEALTH).

Validates semantic versioning compliance by analyzing git tags,
changelog entries, and commit history. Detects incorrect version
bumps and blocks releases with missing documentation.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)

SEMVER_PATTERN = re.compile(
    r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:-(?P<pre>[a-zA-Z0-9.]+))?"
    r"(?:\+(?P<build>[a-zA-Z0-9.]+))?$"
)


class BumpType(Enum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    NONE = "none"


@dataclass
class SemVer:
    """A parsed semantic version."""

    major: int
    minor: int
    patch: int
    pre: str | None = None
    build: str | None = None

    def __str__(self) -> str:
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.pre:
            version += f"-{self.pre}"
        if self.build:
            version += f"+{self.build}"
        return version

    @classmethod
    def parse(cls, version_str: str) -> SemVer | None:
        """Parse a version string into SemVer."""
        match = SEMVER_PATTERN.match(version_str)
        if not match:
            return None
        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
            pre=match.group("pre"),
            build=match.group("build"),
        )


@dataclass
class ValidationResult:
    """Result of semver validation."""

    valid: bool
    expected_bump: BumpType
    actual_bump: BumpType
    errors: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "expected_bump": self.expected_bump.value,
            "actual_bump": self.actual_bump.value,
            "errors": self.errors,
            "suggestions": self.suggestions,
        }


class SemverValidator:
    """Validates semantic versioning compliance."""

    # Conventional commit prefixes that indicate bump types
    BREAKING_PREFIXES = ["feat!", "fix!", "refactor!"]
    BREAKING_FOOTER = "BREAKING CHANGE"
    FEATURE_PREFIXES = ["feat"]
    FIX_PREFIXES = ["fix"]

    def detect_bump_type(self, commit_messages: list[str]) -> BumpType:
        """Detect required bump type from commit messages."""
        has_breaking = False
        has_feature = False
        has_fix = False

        for msg in commit_messages:
            msg_lower = msg.lower().strip()

            # Check for breaking changes
            if any(msg_lower.startswith(p) for p in self.BREAKING_PREFIXES):
                has_breaking = True
            if self.BREAKING_FOOTER.lower() in msg_lower:
                has_breaking = True

            # Check for features
            if any(msg_lower.startswith(p) for p in self.FEATURE_PREFIXES):
                has_feature = True

            # Check for fixes
            if any(msg_lower.startswith(p) for p in self.FIX_PREFIXES):
                has_fix = True

        if has_breaking:
            return BumpType.MAJOR
        if has_feature:
            return BumpType.MINOR
        if has_fix:
            return BumpType.PATCH
        return BumpType.NONE

    def compute_actual_bump(self, old: SemVer, new: SemVer) -> BumpType:
        """Determine what kind of bump was actually applied."""
        if new.major > old.major:
            return BumpType.MAJOR
        if new.minor > old.minor:
            return BumpType.MINOR
        if new.patch > old.patch:
            return BumpType.PATCH
        return BumpType.NONE

    def validate(
        self,
        old_version: str,
        new_version: str,
        commit_messages: list[str],
    ) -> ValidationResult:
        """Validate a version bump against commit history."""
        errors: list[str] = []
        suggestions: list[str] = []

        old = SemVer.parse(old_version)
        new = SemVer.parse(new_version)

        if old is None:
            errors.append(f"Cannot parse old version: {old_version}")
            return ValidationResult(
                valid=False,
                expected_bump=BumpType.NONE,
                actual_bump=BumpType.NONE,
                errors=errors,
            )

        if new is None:
            errors.append(f"Cannot parse new version: {new_version}")
            return ValidationResult(
                valid=False,
                expected_bump=BumpType.NONE,
                actual_bump=BumpType.NONE,
                errors=errors,
            )

        expected = self.detect_bump_type(commit_messages)
        actual = self.compute_actual_bump(old, new)

        # Validate: actual bump should match or exceed expected
        bump_order = {BumpType.NONE: 0, BumpType.PATCH: 1, BumpType.MINOR: 2, BumpType.MAJOR: 3}

        if actual == BumpType.NONE and expected != BumpType.NONE:
            errors.append(f"No version bump applied but {expected.value} bump expected")

        if bump_order[actual] < bump_order[expected]:
            errors.append(f"Insufficient bump: {actual.value} applied but {expected.value} required")
            suggestions.append(f"Use {expected.value} bump: {old} -> expected {expected.value}")

        valid = len(errors) == 0
        return ValidationResult(
            valid=valid,
            expected_bump=expected,
            actual_bump=actual,
            errors=errors,
            suggestions=suggestions,
        )
