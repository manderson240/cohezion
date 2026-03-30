"""Tests for cohezion.services.agent_service — Agent lifecycle and orchestration.

Phase 3c coverage push.
"""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock

import pytest

# Pre-mock missing modules in the services import chain
_MOCKED_MODULES = [
    "cohezion.models",
    "cohezion.models.model_registry",
]
for _mod_name in _MOCKED_MODULES:
    if _mod_name not in sys.modules:
        mock_mod = ModuleType(_mod_name)
        mock_mod.ModelRegistry = MagicMock()  # type: ignore[attr-defined]
        sys.modules[_mod_name] = mock_mod

from cohezion.services.agent_service import (
    AgentConfig,
    AgentService,
    AgentStatus,
)


@pytest.fixture()
def mock_repos():
    """Create mock journey and universe repos."""
    journey_repo = MagicMock()
    journey_repo.create = AsyncMock()
    universe_repo = MagicMock()
    return journey_repo, universe_repo


@pytest.fixture()
def service(mock_repos):
    """Create AgentService with mocked repos."""
    journey_repo, universe_repo = mock_repos
    return AgentService(journey_repo=journey_repo, universe_repo=universe_repo)


@pytest.fixture()
def sample_config():
    """Create a sample agent config."""
    return AgentConfig(
        name="analyst",
        agent_type="analyst",
        model_name="gemma3:4b",
        capabilities=["analysis"],
        priority=3,
    )


class TestAgentConfig:
    """Tests for AgentConfig dataclass."""

    def test_defaults(self):
        """Should have sensible defaults."""
        config = AgentConfig(name="test", agent_type="analyst", model_name="phi3:mini")
        assert config.capabilities == []
        assert config.priority == 3
        assert config.max_concurrency == 1

    def test_custom_values(self):
        """Should accept custom values."""
        config = AgentConfig(
            name="custom",
            agent_type="critic",
            model_name="mistral:7b",
            capabilities=["review", "critique"],
            priority=1,
            max_concurrency=4,
        )
        assert config.name == "custom"
        assert len(config.capabilities) == 2
        assert config.max_concurrency == 4


class TestAgentService:
    """Tests for AgentService agent lifecycle."""

    @pytest.mark.asyncio
    async def test_register_agent(self, service, sample_config):
        """Should register an agent successfully."""
        result = await service.register_agent(sample_config)
        assert result is True
        assert "analyst" in service._active_agents

    @pytest.mark.asyncio
    async def test_register_duplicate_agent(self, service, sample_config):
        """Should reject duplicate registration."""
        await service.register_agent(sample_config)
        result = await service.register_agent(sample_config)
        assert result is False

    @pytest.mark.asyncio
    async def test_unregister_agent(self, service, sample_config):
        """Should unregister an existing agent."""
        await service.register_agent(sample_config)
        result = await service.unregister_agent("analyst")
        assert result is True
        assert "analyst" not in service._active_agents

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_agent(self, service):
        """Should return False for unknown agent."""
        result = await service.unregister_agent("ghost")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_agent_status(self, service, sample_config):
        """Should return status after registration."""
        await service.register_agent(sample_config)
        status = await service.get_agent_status("analyst")
        assert status is not None
        assert isinstance(status, AgentStatus)
        assert status.agent_name == "analyst"
        assert status.is_active is True
        assert status.current_tasks == 0

    @pytest.mark.asyncio
    async def test_get_agent_status_unknown(self, service):
        """Should return None for unknown agent."""
        status = await service.get_agent_status("unknown")
        assert status is None

    @pytest.mark.asyncio
    async def test_get_all_agent_status(self, service, sample_config):
        """Should return all registered agent statuses."""
        await service.register_agent(sample_config)
        config2 = AgentConfig(name="critic", agent_type="critic", model_name="phi3:mini")
        await service.register_agent(config2)
        statuses = await service.get_all_agent_status()
        assert len(statuses) == 2
        assert "analyst" in statuses
        assert "critic" in statuses

    @pytest.mark.asyncio
    async def test_get_agent_config(self, service, sample_config):
        """Should return config for registered agent."""
        await service.register_agent(sample_config)
        config = await service.get_agent_config("analyst")
        assert config is not None
        assert config.model_name == "gemma3:4b"

    @pytest.mark.asyncio
    async def test_get_agent_config_unknown(self, service):
        """Should return None for unknown agent."""
        config = await service.get_agent_config("unknown")
        assert config is None

    @pytest.mark.asyncio
    async def test_list_agents(self, service, sample_config):
        """Should list registered agent names."""
        await service.register_agent(sample_config)
        agents = await service.list_agents()
        assert agents == ["analyst"]

    @pytest.mark.asyncio
    async def test_list_agents_empty(self, service):
        """Should return empty list when no agents registered."""
        agents = await service.list_agents()
        assert agents == []

    @pytest.mark.asyncio
    async def test_execute_task_success(self, service, sample_config, mock_repos):
        """Should execute task and return journey."""
        await service.register_agent(sample_config)
        journey = await service.execute_task("analyst", "Analyze quantum computing")
        assert journey is not None
        assert journey.query == "Analyze quantum computing"
        assert len(journey.steps) >= 1
        # Verify repo was called
        mock_repos[0].create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_task_unregistered_agent(self, service):
        """Should handle unregistered agent gracefully."""
        journey = await service.execute_task("ghost", "test query")
        assert journey is not None
        # Should have an error step
        assert len(journey.steps) >= 1

    @pytest.mark.asyncio
    async def test_execute_task_updates_status(self, service, sample_config):
        """Should increment total_processed after task."""
        await service.register_agent(sample_config)
        await service.execute_task("analyst", "test")
        status = await service.get_agent_status("analyst")
        assert status.total_processed == 1
