"""Autonomous Skill Registration (Story 5.7, FR11).

Auto-registers refined skills with provenance hashing and version
conflict resolution. Version conflicts create incremental versions
rather than overwrites — both versions preserved for Triune review.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass
class RegisteredSkill:
    """A registered skill with provenance tracking."""

    name: str
    version: int
    content: str
    content_hash: str
    provenance_hash: str
    source: str  # "ouroboros" | "mycelium" | "manual"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "content_hash": self.content_hash,
            "provenance_hash": self.provenance_hash,
            "source": self.source,
            "timestamp": self.timestamp,
        }


@dataclass
class RegistrationConflict:
    """A version conflict during skill registration."""

    skill_name: str
    existing_version: int
    new_version: int
    diff_summary: str
    timestamp: float = field(default_factory=time.time)


class AutonomousSkillRegistry:
    """Registry that auto-registers skills with conflict resolution."""

    def __init__(self) -> None:
        self._skills: dict[str, list[RegisteredSkill]] = {}
        self._conflicts: list[RegistrationConflict] = []

    def register(
        self,
        name: str,
        content: str,
        source: str = "ouroboros",
    ) -> tuple[RegisteredSkill, RegistrationConflict | None]:
        """Register a skill, handling version conflicts."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        versions = self._skills.setdefault(name, [])

        # Check for duplicate (same content)
        if versions and versions[-1].content_hash == content_hash:
            return versions[-1], None

        version_num = len(versions) + 1
        provenance_hash = hashlib.sha256(
            f"{name}:{version_num}:{content_hash}".encode()
        ).hexdigest()

        skill = RegisteredSkill(
            name=name,
            version=version_num,
            content=content,
            content_hash=content_hash,
            provenance_hash=provenance_hash,
            source=source,
        )

        conflict = None
        if versions:
            # Version conflict — create new version, preserve both
            conflict = RegistrationConflict(
                skill_name=name,
                existing_version=versions[-1].version,
                new_version=version_num,
                diff_summary=f"Content changed (hash: {content_hash[:16]})",
            )
            self._conflicts.append(conflict)
            logger.info(
                "Skill conflict: %s v%d -> v%d (both preserved)",
                name,
                versions[-1].version,
                version_num,
            )

        versions.append(skill)
        logger.info("Skill registered: %s v%d", name, version_num)
        return skill, conflict

    def get_latest(self, name: str) -> RegisteredSkill | None:
        """Get the latest version of a skill."""
        versions = self._skills.get(name, [])
        return versions[-1] if versions else None

    def get_all_versions(self, name: str) -> list[RegisteredSkill]:
        """Get all versions of a skill."""
        return list(self._skills.get(name, []))

    def get_conflicts(self) -> list[RegistrationConflict]:
        """Get all registration conflicts for Triune review."""
        return list(self._conflicts)

    def list_skills(self) -> list[str]:
        """List all registered skill names."""
        return list(self._skills.keys())
