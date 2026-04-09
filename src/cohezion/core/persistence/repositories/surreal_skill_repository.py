"""SurrealDB Skill Repository - Persistence layer for skill definitions.

Compound Engineering Features:
- Inherits batch operations from BaseRepository
- Automatic metrics collection
- Token-efficient context patterns
"""

import logging
from typing import Any

from cohezion.core.persistence.repositories.base import BaseRepository
from cohezion.core.persistence.repositories.skill_repository import Skill, SkillRepository
from cohezion.core.persistence.surreal_client import SurrealClient


logger = logging.getLogger(__name__)


class SurrealSkillRepository(SkillRepository, BaseRepository[Skill, None]):
    """SurrealDB-backed repository for skill definitions."""

    def __init__(self, client: SurrealClient):
        BaseRepository.__init__(self, table_name="skills")
        self._client = client
        self._table = "skills"
        logger.info("SurrealSkillRepository initialized")

    async def create(self, skill: Skill) -> str:
        """Create a skill record in SurrealDB.

        Returns:
            The ID of the created skill record.
        """
        try:
            # Convert Skill to dict for SurrealDB
            data = {
                "id": f"{self._table}:{skill.name}",
                "name": skill.name,
                "description": skill.description,
                "path": skill.path,
                "version": skill.version,
                "keywords": skill.keywords,
                "metadata": skill.metadata,
                "created_at": self._get_timestamp(),
            }

            query = f"CREATE {self._table} CONTENT $data"
            logger.debug(f"💾 Repository: Executing {query}")
            await self._client.query(query, {"data": data})
            return skill.name

        except Exception as e:
            logger.error(f"Failed to create skill in SurrealDB: {e}")
            raise

    async def get(self, skill_id: str) -> Skill | None:
        """Retrieve a skill by ID from SurrealDB.

        Args:
            skill_id: The skill name (used as ID).

        Returns:
            The Skill if found, None otherwise.
        """
        try:
            # Proper SurrealDB ID selection
            query = f"SELECT * FROM `{self._table}:{skill_id}`"
            result = await self._client.query(query)

            if not result or not result[0].get("result"):
                return None

            data = result[0]["result"][0]
            return self._dict_to_skill(data)

        except Exception as e:
            logger.error(f"Failed to get skill from SurrealDB: {e}")
            return None

    async def get_by_name(self, name: str) -> Skill | None:
        """Retrieve a skill by name from SurrealDB.

        Args:
            name: The skill name to search for.

        Returns:
            The Skill if found, None otherwise.
        """
        return await self.get(name)

    async def get_all(self, limit: int = 100) -> list[Skill]:
        """Retrieve all skills from SurrealDB.

        Args:
            limit: Maximum number of skills to return.

        Returns:
            List of Skill objects.
        """
        try:
            query = f"SELECT * FROM {self._table} LIMIT {limit}"
            result = await self._client.query(query)

            if not result or not result[0].get("result"):
                return []

            skills = []
            for data in result[0]["result"]:
                skill = self._dict_to_skill(data)
                if skill:
                    skills.append(skill)
            return skills

        except Exception as e:
            logger.error(f"Failed to get all skills from SurrealDB: {e}")
            return []

    async def update(self, skill: Skill) -> bool:
        """Update an existing skill record in SurrealDB.

        Args:
            skill: The Skill object with updated values.

        Returns:
            True if the skill was updated, False otherwise.
        """
        try:
            # Convert Skill to dict for SurrealDB
            data = {
                "name": skill.name,
                "description": skill.description,
                "path": skill.path,
                "version": skill.version,
                "keywords": skill.keywords,
                "metadata": skill.metadata,
                "updated_at": self._get_timestamp(),
            }

            query = f"UPDATE {self._table}:{skill.name} MERGE $data"
            logger.debug(f"💾 Repository: Executing {query}")
            await self._client.query(query, {"data": data})
            return True

        except Exception as e:
            logger.error(f"Failed to update skill in SurrealDB: {e}")
            return False

    async def delete(self, skill_id: str) -> bool:
        """Delete a skill record from SurrealDB.

        Args:
            skill_id: The skill name to delete.

        Returns:
            True if the skill was deleted, False otherwise.
        """
        try:
            query = f"DELETE {self._table}:{skill_id}"
            logger.debug(f"💾 Repository: Executing {query}")
            await self._client.query(query)
            return True

        except Exception as e:
            logger.error(f"Failed to delete skill from SurrealDB: {e}")
            return False

    def _dict_to_skill(self, data: dict[str, Any]) -> Skill | None:
        """Helper to convert SurrealDB dict to Skill."""
        try:
            return Skill(
                name=data.get("name", ""),
                description=data.get("description", ""),
                path=data.get("path", ""),
                version=data.get("version", "0.1.0"),
                keywords=data.get("keywords", []),
                metadata=data.get("metadata", {}),
            )
        except Exception as e:
            logger.error(f"Failed to convert dict to Skill: {e}")
            return None

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime

        return datetime.now().isoformat()
