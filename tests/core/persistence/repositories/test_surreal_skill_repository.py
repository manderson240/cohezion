"""Tests for SurrealSkillRepository."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from cohezion.core.persistence.repositories.skill_repository import Skill
from cohezion.core.persistence.repositories.surreal_skill_repository import (
    SurrealSkillRepository,
)
from cohezion.core.persistence.surreal_client import SurrealClient


@pytest.fixture
def mock_surreal_client():
    """Create a mock SurrealClient."""
    with patch("cohezion.core.persistence.surreal_client.SurrealClient") as mock_cls:
        instance = mock_cls.return_value
        instance.query = AsyncMock()
        yield instance


@pytest.fixture
def skill_repo(mock_surreal_client):
    """Create a SurrealSkillRepository instance."""
    return SurrealSkillRepository(mock_surreal_client)


@pytest.fixture
def sample_skill():
    """Create a sample skill for testing."""
    return Skill(
        name="test_skill",
        description="A test skill",
        path="/path/to/skill.md",
        version="1.0.0",
        keywords=["test", "skill"],
        metadata={"author": "tester"},
    )


class TestSurrealSkillRepository:
    """Tests for SurrealSkillRepository."""

    @pytest.mark.asyncio
    async def test_create_skill(self, skill_repo, mock_surreal_client, sample_skill):
        """Test creating a skill."""
        # Setup
        mock_surreal_client.query.return_value = [
            {
                "result": [
                    {
                        "id": "skills:test_skill",
                        "name": "test_skill",
                        "description": "A test skill",
                        "path": "/path/to/skill.md",
                        "version": "1.0.0",
                        "keywords": ["test", "skill"],
                        "metadata": {"author": "tester"},
                        "created_at": "2023-01-01T00:00:00",
                    }
                ]
            }
        ]

        # Execute
        result = await skill_repo.create(sample_skill)

        # Verify
        assert result == "test_skill"
        mock_surreal_client.query.assert_called_once()
        call_args = mock_surreal_client.query.call_args
        assert "CREATE skills CONTENT" in call_args[0][0]
        # For CREATE, SurrealDB returns the data nested under 'result' -> [0] -> actual data
        assert call_args[0][1]["data"]["name"] == "test_skill"

    @pytest.mark.asyncio
    async def test_get_skill_found(self, skill_repo, mock_surreal_client):
        """Test getting a skill that exists."""
        # Setup
        mock_surreal_client.query.return_value = [
            {
                "result": [
                    {
                        "id": "skills:test_skill",
                        "name": "test_skill",
                        "description": "A test skill",
                        "path": "/path/to/skill.md",
                        "version": "1.0.0",
                        "keywords": ["test", "skill"],
                        "metadata": {"author": "tester"},
                        "created_at": "2023-01-01T00:00:00",
                    }
                ]
            }
        ]

        # Execute
        result = await skill_repo.get("test_skill")

        # Verify
        assert result is not None
        assert result.name == "test_skill"
        assert result.description == "A test skill"
        assert result.path == "/path/to/skill.md"
        assert result.version == "1.0.0"
        assert result.keywords == ["test", "skill"]
        assert result.metadata == {"author": "tester"}

    @pytest.mark.asyncio
    async def test_get_skill_not_found(self, skill_repo, mock_surreal_client):
        """Test getting a skill that doesn't exist."""
        # Setup
        mock_surreal_client.query.return_value = [{"result": []}]

        # Execute
        result = await skill_repo.get("nonexistent_skill")

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_name(self, skill_repo, mock_surreal_client):
        """Test getting a skill by name (delegates to get)."""
        # Setup
        mock_surreal_client.query.return_value = [
            {
                "result": [
                    {
                        "id": "skills:test_skill",
                        "name": "test_skill",
                        "description": "A test skill",
                        "path": "/path/to/skill.md",
                        "version": "1.0.0",
                        "keywords": ["test", "skill"],
                        "metadata": {"author": "tester"},
                        "created_at": "2023-01-01T00:00:00",
                    }
                ]
            }
        ]

        # Execute
        result = await skill_repo.get_by_name("test_skill")

        # Verify
        assert result is not None
        assert result.name == "test_skill"
        mock_surreal_client.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_skills(self, skill_repo, mock_surreal_client):
        """Test getting all skills."""
        # Setup
        mock_surreal_client.query.return_value = [
            {
                "result": [
                    {
                        "id": "skills:skill1",
                        "name": "skill1",
                        "description": "First skill",
                        "path": "/path/to/skill1.md",
                        "version": "1.0.0",
                        "keywords": ["skill1"],
                        "metadata": {},
                        "created_at": "2023-01-01T00:00:00",
                    },
                    {
                        "id": "skills:skill2",
                        "name": "skill2",
                        "description": "Second skill",
                        "path": "/path/to/skill2.md",
                        "version": "2.0.0",
                        "keywords": ["skill2"],
                        "metadata": {},
                        "created_at": "2023-01-02T00:00:00",
                    },
                ]
            }
        ]

        # Execute
        result = await skill_repo.get_all(limit=10)

        # Verify
        assert len(result) == 2
        assert result[0].name == "skill1"
        assert result[1].name == "skill2"
        mock_surreal_client.query.assert_called_once()
        call_args = mock_surreal_client.query.call_args
        assert "SELECT * FROM skills LIMIT 10" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_update_skill(self, skill_repo, mock_surreal_client):
        """Test updating a skill."""
        # Setup
        updated_skill = Skill(
            name="test_skill",
            description="Updated test skill",
            path="/updated/path/to/skill.md",
            version="2.0.0",
            keywords=["updated", "test"],
            metadata={"author": "updater"},
        )

        # Execute
        result = await skill_repo.update(updated_skill)

        # Verify
        assert result is True
        mock_surreal_client.query.assert_called_once()
        call_args = mock_surreal_client.query.call_args
        assert "UPDATE skills:" in call_args[0][0]
        assert "MERGE" in call_args[0][0]
        # For UPDATE, the data is passed directly in the data parameter
        assert call_args[0][1]["data"]["description"] == "Updated test skill"

    @pytest.mark.asyncio
    async def test_delete_skill(self, skill_repo, mock_surreal_client):
        """Test deleting a skill."""
        # Execute
        result = await skill_repo.delete("test_skill")

        # Verify
        assert result is True
        mock_surreal_client.query.assert_called_once()
        call_args = mock_surreal_client.query.call_args
        assert "DELETE skills:test_skill" in call_args[0][0]
