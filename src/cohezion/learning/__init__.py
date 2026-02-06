"""Stub for cohezion.learning — original module was removed.

Provides a no-op skill generator so tests can import cleanly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Pattern:
    name: str = ""
    description: str = ""
    example: str = ""
    tags: list[str] = field(default_factory=list)
    occurrences: int = 1


class PatternDetector:
    """No-op pattern detector."""

    def record(
        self,
        name: str,
        description: str,
        example: str,
        tags: list[str] | None = None,
    ) -> Pattern:
        return Pattern(
            name=name,
            description=description,
            example=example,
            tags=tags or [],
            occurrences=1,
        )


class SkillGenerator:
    """No-op skill generator."""

    def __init__(self) -> None:
        self.detector = PatternDetector()


_instance: SkillGenerator | None = None


def get_skill_generator() -> SkillGenerator:
    """Return a singleton skill generator."""
    global _instance
    if _instance is None:
        _instance = SkillGenerator()
    return _instance
