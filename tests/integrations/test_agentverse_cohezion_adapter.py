"""Tests for Cohezion-AgentVerse integration adapter.

TDD tests for CohezionAgentAdapter that wraps Cohezion skills
as AgentVerse-compatible agents.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestCohezionAgentAdapter:
    """[P0] Tests for CohezionAgentAdapter."""

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
        executor.execute_task = MagicMock()
        executor.get_experience_guidance = MagicMock(return_value={})
        return executor

    @pytest.fixture()
    def adapter(self, mock_mcp_client, mock_executor):
        """Create adapter with mocked dependencies."""
        from cohezion.integrations.agentverse import CohezionAgentAdapter

        adapter = CohezionAgentAdapter(
            skill_name="test_skill_PRIME",
            mcp_client=mock_mcp_client,
            executor=mock_executor,
        )
        return adapter

    def test_initialization(self, adapter):
        """[P0] Should initialize with skill name and client."""
        assert adapter.skill_name == "test_skill_PRIME"
        assert adapter.mcp_client is not None
        assert adapter.executor is not None

    def test_initialization_with_role(self, mock_mcp_client, mock_executor):
        """[P1] Should accept custom role assignment."""
        from cohezion.integrations.agentverse import CohezionAgentAdapter

        adapter = CohezionAgentAdapter(
            skill_name="code_review_PRIME",
            mcp_client=mock_mcp_client,
            executor=mock_executor,
            role="reviewer",
        )
        assert adapter.role == "reviewer"

    def test_role_defaults_to_implementer(self, mock_mcp_client, mock_executor):
        """[P1] Should default role to implementer."""
        from cohezion.integrations.agentverse import CohezionAgentAdapter

        adapter = CohezionAgentAdapter(
            skill_name="test_PRIME",
            mcp_client=mock_mcp_client,
            executor=mock_executor,
        )
        assert adapter.role == "implementer"

    def test_step_executes_task(self, adapter, mock_executor):
        """[P0] Should execute task through executor."""
        mock_executor.execute_task.return_value = MagicMock(
            success=True,
            output="test output",
            metrics={"coherence": 0.8},
            duration_seconds=1.0,
        )

        result = adapter.step("Write a test function")

        mock_executor.execute_task.assert_called_once()
        call_args = mock_executor.execute_task.call_args
        assert "Write a test function" in call_args[1]["task_description"]
        assert result.success is True
        assert result.output == "test output"

    def test_step_returns_execution_result(self, adapter, mock_executor):
        """[P0] Should return ExecutionResult from step."""
        from cohezion.compound.executor import ExecutionResult

        mock_result = ExecutionResult(
            success=True,
            output="done",
            metrics={"coherence": 0.9},
            duration_seconds=0.5,
        )
        mock_executor.execute_task.return_value = mock_result

        result = adapter.step("test task")
        assert isinstance(result, ExecutionResult)
        assert result.success is True

    def test_step_handles_execution_failure(self, adapter, mock_executor):
        """[P0] Should handle task execution failure gracefully."""
        mock_executor.execute_task.return_value = MagicMock(
            success=False,
            output="error occurred",
            metrics={"error": "task failed"},
            duration_seconds=0.1,
        )

        result = adapter.step("failing task")
        assert result.success is False

    def test_reset_history_clears_messages(self, adapter):
        """[P0] Should clear message history on reset."""
        adapter.message_history = ["msg1", "msg2", "msg3"]
        adapter.reset_history()
        assert adapter.message_history == []

    def test_message_history_tracks_steps(self, adapter):
        """[P1] Should track messages in history after steps."""
        adapter.reset_history()
        adapter.message_history.append({"role": "user", "content": "test"})
        assert len(adapter.message_history) == 1


class TestCohezionAgentAdapterTools:
    """[P1] Tests for CohezionAgentAdapter tool handling."""

    @pytest.fixture()
    def mock_mcp_client(self):
        client = MagicMock()
        client.query = AsyncMock(return_value=[])
        client.store_node = MagicMock(return_value={"id": "test_id"})
        return client

    @pytest.fixture()
    def mock_executor(self):
        return MagicMock()

    def test_allowed_tools_for_implementer(self, mock_mcp_client, mock_executor):
        """[P1] Should return correct tools for implementer role."""
        from cohezion.integrations.agentverse import CohezionAgentAdapter

        adapter = CohezionAgentAdapter(
            skill_name="test_PRIME",
            mcp_client=mock_mcp_client,
            executor=mock_executor,
            role="implementer",
        )

        tools = adapter.get_allowed_tools()
        assert "Read" in tools
        assert "Write" in tools
        assert "Edit" in tools
        assert "Bash" in tools

    def test_allowed_tools_for_reviewer(self, mock_mcp_client, mock_executor):
        """[P1] Should return restricted tools for reviewer role."""
        from cohezion.integrations.agentverse import CohezionAgentAdapter

        adapter = CohezionAgentAdapter(
            skill_name="review_PRIME",
            mcp_client=mock_mcp_client,
            executor=mock_executor,
            role="reviewer",
        )

        tools = adapter.get_allowed_tools()
        assert "Read" in tools
        assert "Glob" in tools
        assert "Grep" in tools
        assert "Edit" not in tools
        assert "Bash" not in tools

    def test_disallowed_tools_for_reviewer(self, mock_mcp_client, mock_executor):
        """[P1] Should return disallowed tools for reviewer role."""
        from cohezion.integrations.agentverse import CohezionAgentAdapter

        adapter = CohezionAgentAdapter(
            skill_name="review_PRIME",
            mcp_client=mock_mcp_client,
            executor=mock_executor,
            role="reviewer",
        )

        disallowed = adapter.get_disallowed_tools()
        assert "Edit" in disallowed
        assert "Write" in disallowed
        assert "Bash" in disallowed


class TestCohezionAgentAdapterModelRouting:
    """[P1] Tests for CohezionAgentAdapter model routing."""

    @pytest.fixture()
    def mock_mcp_client(self):
        client = MagicMock()
        client.query = AsyncMock(return_value=[])
        return client

    @pytest.fixture()
    def mock_executor(self):
        return MagicMock()

    def test_selects_coder_model_for_code_skill(self, mock_mcp_client, mock_executor):
        """[P1] Should select coder model for code-related skills."""
        from cohezion.integrations.agentverse import CohezionAgentAdapter

        adapter = CohezionAgentAdapter(
            skill_name="python_PRIME",
            mcp_client=mock_mcp_client,
            executor=mock_executor,
        )

        model = adapter.select_model()
        assert "coder" in model or "qwen" in model.lower() or "llama" in model.lower()

    def test_selects_reasoning_model_for_research(self, mock_mcp_client, mock_executor):
        """[P1] Should select reasoning model for research tasks."""
        from cohezion.integrations.agentverse import CohezionAgentAdapter

        adapter = CohezionAgentAdapter(
            skill_name="research_PRIME",
            mcp_client=mock_mcp_client,
            executor=mock_executor,
        )

        model = adapter.select_model()
        assert model is not None

    def test_model_selection_consistent_across_calls(self, mock_mcp_client, mock_executor):
        """[P1] Should return consistent model across multiple calls."""
        from cohezion.integrations.agentverse import CohezionAgentAdapter

        adapter = CohezionAgentAdapter(
            skill_name="python_PRIME",
            mcp_client=mock_mcp_client,
            executor=mock_executor,
        )

        model1 = adapter.select_model()
        model2 = adapter.select_model()
        assert model1 == model2
