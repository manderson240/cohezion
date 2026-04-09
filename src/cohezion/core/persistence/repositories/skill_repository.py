"""Skill Repository - Dataclass and abstract definitions for skill persistence."""

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
        """Create a skill record.

        Returns:
            The ID of the created skill record.
        """

    @abstractmethod
    async def get(self, skill_id: str) -> Skill | None:
        """Retrieve a skill by ID.

        Returns:
            The Skill if found, None otherwise.
        """

    @abstractmethod
    async def get_by_name(self, name: str) -> Skill | None:
        """Retrieve a skill by name.

        Returns:
            The Skill if found, None otherwise.
        """

    @abstractmethod
    async def get_all(self, limit: int = 100) -> list[Skill]:
        """Retrieve all skills.

        Args:
            limit: Maximum number of skills to return.

        Returns:
            List of Skill objects.
        """

    @abstractmethod
    async def update(self, skill: Skill) -> bool:
        """Update an existing skill record.

        Args:
            skill: The Skill object with updated values.

        Returns:
            True if the skill was updated, False otherwise.
        """

    @abstractmethod
    async def delete(self, skill_id: str) -> bool:
        """Delete a skill record.

        Args:
            skill_id: The ID of the skill to delete.

        Returns:
            True if the skill was deleted, False otherwise.
        """
