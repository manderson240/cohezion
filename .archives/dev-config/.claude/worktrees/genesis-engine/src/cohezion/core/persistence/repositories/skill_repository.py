"""Skill Repository - Dataclass and abstract definitions for skill persistence.

TODO: Implement full SkillRepository abstract base class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Skill:
    """A skill definition in the Cohezion capability registry."""

    name: str = ""
    description: str = ""
    path: str = ""
    version: str = "0.1.0"
    keywords: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class SkillRepository(ABC):
    """Abstract base class for skill persistence."""

    @abstractmethod
    async def create(self, skill: Skill) -> str:
        """Create a skill record."""

    @abstractmethod
    async def get(self, skill_id: str) -> Skill | None:
        """Retrieve a skill by ID."""

    @abstractmethod
    async def get_by_name(self, name: str) -> Skill | None:
        """Retrieve a skill by name."""

    @abstractmethod
    async def get_all(self, limit: int = 100) -> list[Skill]:
        """Retrieve all skills."""
