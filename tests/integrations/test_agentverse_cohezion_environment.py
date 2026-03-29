"""Tests for CohezionEnvironment - AgentVerse simulation environment.

TDD tests for CohezionEnvironment that wraps Cohezion vault/knowledge
as an AgentVerse-compatible simulation environment.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestCohezionEnvironment:
    """[P0] Tests for CohezionEnvironment."""

    @pytest.fixture()
    def mock_mcp_client(self):
        """Create mock MCP client."""
        client = MagicMock()
        client.query = AsyncMock(return_value=[])
        client.store_node = MagicMock(return_value={"id": "test_id"})
        return client

    @pytest.fixture()
    def mock_executor(self):
        """Create mock CompoundExecutor."""
        executor = MagicMock()
        return executor

    @pytest.fixture()
    def environment(self, mock_mcp_client, mock_executor):
        """Create environment with mocked dependencies."""
        from cohezion.integrations.agentverse import CohezionEnvironment

        env = CohezionEnvironment(
            mcp_client=mock_mcp_client,
            executor=mock_executor,
        )
        return env

    def test_initialization(self, environment, mock_mcp_client):
        """[P0] Should initialize with MCP client."""
        assert environment.mcp_client == mock_mcp_client
        assert environment.agents == []

    def test_initialization_with_agents(self, environment, mock_mcp_client):
        """[P1] Should initialize with list of agents."""
        mock_agent = MagicMock()
        mock_agent.name = "test_agent"
        environment.agents = [mock_agent]
        assert len(environment.agents) == 1

    def test_reset_clears_agents(self, environment):
        """[P0] Should clear agents on reset."""
        mock_agent = MagicMock()
        environment.agents = [mock_agent]
        environment.reset()
        assert environment.agents == []

    def test_step_not_implemented(self, environment):
        """[P0] Should raise NotImplementedError for step."""
        with pytest.raises(NotImplementedError):
            environment.step()

    def test_get_context_returns_vault_data(self, environment, mock_mcp_client):
        """[P1] Should return context from vault queries."""
        mock_mcp_client.query.return_value = [{"data": "test_context"}]
        context = environment.get_context()
        assert context is not None


class TestCohezionSimulationEnvironment:
    """[P1] Tests for CohezionSimulationEnvironment."""

    @pytest.fixture()
    def mock_mcp_client(self):
        """Create mock MCP client."""
        client = MagicMock()
        client.query = AsyncMock(return_value=[])
        client.store_node = MagicMock(return_value={"id": "test_id"})
        return client

    @pytest.fixture()
    def mock_executor(self):
        """Create mock CompoundExecutor."""
        executor = MagicMock()
        return executor

    @pytest.fixture()
    def sim_env(self, mock_mcp_client, mock_executor):
        """Create simulation environment."""
        from cohezion.integrations.agentverse import CohezionSimulationEnvironment

        env = CohezionSimulationEnvironment(
            mcp_client=mock_mcp_client,
            executor=mock_executor,
        )
        return env

    def test_initialization(self, sim_env):
        """[P0] Should initialize simulation environment."""
        assert sim_env.agents == []
        assert sim_env.n_round == 0

    def test_reset_initializes_round(self, sim_env):
        """[P0] Should reset round counter."""
        sim_env.n_round = 5
        sim_env.reset()
        assert sim_env.n_round == 0

    def test_add_agent(self, sim_env):
        """[P1] Should add agent to environment."""
        mock_agent = MagicMock()
        mock_agent.name = "agent_1"
        sim_env.add_agent(mock_agent)
        assert len(sim_env.agents) == 1
        assert sim_env.agents[0].name == "agent_1"

    def test_add_multiple_agents(self, sim_env):
        """[P1] Should add multiple agents."""
        for i in range(3):
            mock_agent = MagicMock()
            mock_agent.name = f"agent_{i}"
            sim_env.add_agent(mock_agent)
        assert len(sim_env.agents) == 3

    def test_get_observation_returns_dict(self, sim_env):
        """[P1] Should return observation as dict."""
        obs = sim_env.get_observation()
        assert isinstance(obs, dict)


class TestCohezionTaskSolvingEnvironment:
    """[P1] Tests for CohezionTaskSolvingEnvironment."""

    @pytest.fixture()
    def mock_mcp_client(self):
        """Create mock MCP client."""
        client = MagicMock()
        client.query = AsyncMock(return_value=[])
        return client

    @pytest.fixture()
    def mock_executor(self):
        """Create mock CompoundExecutor."""
        executor = MagicMock()
        return executor

    @pytest.fixture()
    def task_env(self, mock_mcp_client, mock_executor):
        """Create task-solving environment."""
        from cohezion.integrations.agentverse import CohezionTaskSolvingEnvironment

        env = CohezionTaskSolvingEnvironment(
            mcp_client=mock_mcp_client,
            executor=mock_executor,
            task_description="Solve a coding problem",
        )
        return env

    def test_initialization_with_task(self, task_env):
        """[P0] Should initialize with task description."""
        assert task_env.task_description == "Solve a coding problem"
        assert task_env.n_round == 0

    def test_is_multi_agent_returns_true(self, task_env):
        """[P1] Should identify as multi-agent environment."""
        assert task_env.is_multi_agent() is True

    def test_get_task_returns_description(self, task_env):
        """[P1] Should return task description."""
        assert task_env.get_task() == "Solve a coding problem"
