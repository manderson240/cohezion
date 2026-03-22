"""Skill Evolution Diffs (Story 5.5, FR18).

Tracks before/after changes to skill definitions and generates
structured diffs for verification. Additions are marked as
Biolume (green), removals as Plasma (red).
"""

from __future__ import annotations

import difflib
import hashlib
import logging
import time
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass
class SkillVersion:
    """A versioned snapshot of a skill definition."""

    skill_name: str
    version: int
    content: str
    content_hash: str = ""
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.content.encode()).hexdigest()


@dataclass
class SkillDiff:
    """A diff between two versions of a skill definition."""

    skill_name: str
    version_before: int
    version_after: int
    additions: int  # Lines added (Biolume)
    removals: int  # Lines removed (Plasma)
    diff_text: str  # Unified diff
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "skill_name": self.skill_name,
            "version_before": self.version_before,
            "version_after": self.version_after,
            "additions": self.additions,
            "removals": self.removals,
            "diff_text": self.diff_text,
            "timestamp": self.timestamp,
        }


class SkillEvolutionTracker:
    """Tracks skill evolution and generates diffs."""

    def __init__(self) -> None:
        self._versions: dict[str, list[SkillVersion]] = {}
        self._diffs: list[SkillDiff] = []

    def record_version(self, skill_name: str, content: str) -> SkillVersion:
        """Record a new version of a skill definition."""
        versions = self._versions.setdefault(skill_name, [])
        version_num = len(versions) + 1
        sv = SkillVersion(
            skill_name=skill_name,
            version=version_num,
            content=content,
        )
        versions.append(sv)

        # Generate diff if there's a previous version
        if len(versions) >= 2:
            diff = self._generate_diff(versions[-2], sv)
            self._diffs.append(diff)
            logger.info(
                "Skill %s evolved: v%d -> v%d (+%d/-%d)",
                skill_name,
                diff.version_before,
                diff.version_after,
                diff.additions,
                diff.removals,
            )

        return sv

    def _generate_diff(self, before: SkillVersion, after: SkillVersion) -> SkillDiff:
        """Generate a unified diff between two versions."""
        before_lines = before.content.splitlines(keepends=True)
        after_lines = after.content.splitlines(keepends=True)

        diff_lines = list(
            difflib.unified_diff(
                before_lines,
                after_lines,
                fromfile=f"{before.skill_name} v{before.version}",
                tofile=f"{after.skill_name} v{after.version}",
            )
        )

        additions = sum(1 for ln in diff_lines if ln.startswith("+") and not ln.startswith("+++"))
        removals = sum(1 for ln in diff_lines if ln.startswith("-") and not ln.startswith("---"))

        return SkillDiff(
            skill_name=before.skill_name,
            version_before=before.version,
            version_after=after.version,
            additions=additions,
            removals=removals,
            diff_text="".join(diff_lines),
        )

    def get_diffs(self, skill_name: str | None = None) -> list[SkillDiff]:
        """Get diffs, optionally filtered by skill name."""
        if skill_name:
            return [d for d in self._diffs if d.skill_name == skill_name]
        return list(self._diffs)

    def get_latest_version(self, skill_name: str) -> SkillVersion | None:
        """Get the latest version of a skill."""
        versions = self._versions.get(skill_name, [])
        return versions[-1] if versions else None

    def get_evolution_report(self) -> list[dict]:
        """Export all diffs for visualization."""
        return [d.to_dict() for d in self._diffs]
