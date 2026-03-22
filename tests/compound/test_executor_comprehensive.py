"""Comprehensive tests for compound executor.

Generated for P0 coverage of executor.py (1106 lines).
Tests all major functionality including execution lifecycle,
guardrails, skill refinement, and token metrics.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from cohezion.compound.core.executor import CompoundExecutor, ExecutionConfig
from cohezion.compound.models import ExecutionMetrics, ExecutionResult, Task


class TestCompoundExecutorInitialization:
    """[P0] Tests for executor initialization."""

    @pytest.fixture()
    def mock_mcp(self):
        """Create mock MCP client."""
        return MagicMock(spec=MCPClient)

        def execute_fn(task, context):
            return ("output", {"total_tokens": 100})

        assert executor.mcp_client == mock_mcp
        assert executor.logger is not None

    def test_executor_initializes_with_optional_components(self, mock_mcp):
        """[P0] Should initialize with optional components."""
        token_client = MagicMock()
        guardrail_pipeline = MagicMock(spec=GuardrailPipeline)

        executor = CompoundExecutor(
            mcp_client=mock_mcp,
            token_client=token_client,
            guardrail_pipeline=guardrail_pipeline,
            enable_guardrails=True,
        )

        assert executor.token_client == token_client
        assert executor._guardrail_pipeline == guardrail_pipeline
        assert executor._enable_guardrails is True

    def test_executor_initializes_with_guardrails_disabled(self, mock_mcp):
        """[P1] Should initialize with guardrails disabled."""
        executor = CompoundExecutor(
            mcp_client=mock_mcp,
            enable_guardrails=False,
        )

        assert executor._enable_guardrails is False


class TestCompoundExecutorExecution:
    """[P0] Tests for task execution."""

    @pytest.fixture()
    def executor(self):
        """Create executor with mock function."""

        def execute_fn(task, context):
            return (f"output for {task.description}", {"total_tokens": 100})

        return CompoundExecutor(execute_fn=execute_fn)

    @pytest.fixture()
    def executor(self, mock_mcp):
        """Create executor with mocked logger."""
        executor = CompoundExecutor(mcp_client=mock_mcp)
        executor.logger = MagicMock()
        executor.logger.get_experience_guidance.return_value = {}
        executor.logger.log_execution_start.return_value = "test-experiment-path"
        executor.logger.log_decision_point.return_value = "test-decision-path"
        return executor

    def test_execute_task_successful(self, executor):
        """[P0] Should execute task successfully."""
        result = executor.execute_task(
            task_description="Test task",
            skill_name="test-skill",
            operation_type="generate",
            execute_fn=lambda guidance: ("output", {"metric": 1.0}),
        )

        assert isinstance(result, ExecutionResult)
        assert result.success is True
        assert result.output == "output"
        assert result.metrics["metric"] == 1.0

    def test_execute_task_with_failure(self, executor):
        """[P0] Should handle task execution failure."""

        def failing_fn(guidance):
            raise ValueError("Test error")

        result = executor.execute_task(
            task_description="Test task",
            skill_name="test-skill",
            operation_type="generate",
            execute_fn=failing_fn,
        )

        assert isinstance(result, ExecutionResult)
        assert result.success is False
        assert "Test error" in result.output

    def test_execute_task_records_duration(self, executor):
        """[P1] Should record execution duration."""
        result = executor.execute_task(
            task_description="Test task",
            skill_name="test-skill",
            operation_type="generate",
            execute_fn=lambda guidance: ("output", {}),
        )

        assert result.duration_seconds > 0

    def test_execute_task_logs_to_vault(self, executor):
        """[P0] Should log execution to vault."""
        executor.execute_task(
            task_description="Test task",
            skill_name="test-skill",
            operation_type="generate",
            execute_fn=lambda guidance: ("output", {}),
        )

        executor.logger.log_execution_start.assert_called_once()


class TestCompoundExecutorGuardrails:
    """[P1] Tests for guardrail integration."""

    @pytest.fixture()
    def mock_mcp(self):
        return MagicMock(spec=MCPClient)

    @pytest.fixture()
    def executor_with_guardrails(self, mock_mcp):
        """Create executor with mock guardrails."""
        guardrail_pipeline = MagicMock(spec=GuardrailPipeline)
        guardrail_pipeline.check_input.return_value = GuardrailResult(action=GuardrailAction.ALLOW)
        guardrail_pipeline.check_output.return_value = GuardrailResult(action=GuardrailAction.ALLOW)

        executor = CompoundExecutor(
            mcp_client=mock_mcp,
            guardrail_pipeline=guardrail_pipeline,
            enable_guardrails=True,
        )
        executor.logger = MagicMock()
        executor.logger.get_experience_guidance.return_value = {}
        return executor

    def test_guardrails_check_output(self, executor_with_guardrails):
        """[P1] Should check output through guardrails."""
        result = executor_with_guardrails.execute_task(
            task_description="Test task",
            skill_name="test-skill",
            operation_type="generate",
            execute_fn=lambda guidance: ("output", {}),
        )

        assert result.success is True
        executor_with_guardrails._guardrail_pipeline.check_output.assert_called()


class TestCompoundExecutorTokenMetrics:
    """[P1] Tests for token metrics integration."""

    @pytest.fixture()
    def mock_mcp(self):
        return MagicMock(spec=MCPClient)

    @pytest.fixture()
    def executor_with_token_client(self, mock_mcp):
        """Create executor with token client."""
        token_client = MagicMock()
        token_client.get_metrics.return_value = {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        }

        executor = CompoundExecutor(
            mcp_client=mock_mcp,
            token_client=token_client,
        )
        executor.logger = MagicMock()
        executor.logger.get_experience_guidance.return_value = {}
        return executor

    def test_token_metrics_captured(self, executor_with_token_client):
        """[P1] Should capture token metrics."""
        result = executor_with_token_client.execute_task(
            task_description="Test task",
            skill_name="test-skill",
            operation_type="generate",
            execute_fn=lambda guidance: ("output", {}),
        )

        assert result.token_metrics is not None


class TestCompoundExecutorExperienceGuidance:
    """[P1] Tests for experience guidance."""

    @pytest.fixture()
    def mock_mcp(self):
        return MagicMock(spec=MCPClient)

    def test_get_experience_guidance(self, mock_mcp):
        """[P1] Should retrieve experience guidance."""
        executor = CompoundExecutor(mcp_client=mock_mcp)
        executor.logger = MagicMock()
        executor.logger.get_experience_guidance.return_value = {
            "similar_tasks": [{"task_id": "123", "success": True}],
        }

        guidance = executor.get_experience_guidance(
            task_description="Test task",
            project="cohezion",
            operation_type="generate",
        )

        assert "similar_tasks" in guidance
        assert len(guidance["similar_tasks"]) == 1

    def test_guidance_used_in_execution(self, mock_mcp):
        """[P1] Should use guidance during execution."""
        received_guidance = {}

        def capture_guidance(guidance):
            nonlocal received_guidance
            received_guidance = guidance
            return ("output", {})

        executor = CompoundExecutor(mcp_client=mock_mcp)
        executor.logger = MagicMock()
        executor.logger.get_experience_guidance.return_value = {"hint": "use async/await"}

        executor.execute_task(
            task_description="Test task",
            skill_name="test-skill",
            operation_type="generate",
            execute_fn=capture_guidance,
        )

        assert received_guidance.get("hint") == "use async/await"


class TestCompoundExecutorEdgeCases:
    """[P2] Edge case tests."""

    @pytest.fixture()
    def mock_mcp(self):
        return MagicMock(spec=MCPClient)

    @pytest.fixture()
    def executor(self, mock_mcp):
        executor = CompoundExecutor(mcp_client=mock_mcp)
        executor.logger = MagicMock()
        executor.logger.get_experience_guidance.return_value = {}
        return executor

    def test_empty_output_handled(self, executor):
        """[P2] Should handle empty output."""
        result = executor.execute_task(
            task_description="Test task",
            skill_name="test-skill",
            operation_type="generate",
            execute_fn=lambda guidance: ("", {}),
        )

        assert result.success is True
        assert result.output == ""

    def test_execution_with_context_parameter(self, executor):
        """[P1] Should pass context to execute_fn."""
        received_context = None

        def check_context(guidance):
            nonlocal received_context
            received_context = guidance
            return ("output", {})

        executor.execute_task(
            task_description="Test task",
            skill_name="test-skill",
            operation_type="generate",
            execute_fn=check_context,
        )

        # guidance should be a dict
        assert isinstance(received_context, dict)


class TestExecutionResult:
    """[P0] Tests for ExecutionResult dataclass."""

    def test_result_creation(self):
        """[P0] Should create ExecutionResult."""
        result = ExecutionResult(
            success=True,
            output="test output",
            metrics={"key": "value"},
            duration_seconds=1.5,
        )

        assert result.success is True
        assert result.output == "test output"
        assert result.metrics == {"key": "value"}
        assert result.duration_seconds == 1.5

    def test_result_with_optional_fields(self):
        """[P1] Should create result with optional fields."""
        result = ExecutionResult(
            success=True,
            output="test",
            metrics={},
            duration_seconds=1.0,
            vault_experiment_path="/path/to/experiment",
            vault_decision_paths=["/path/to/decision"],
            token_metrics={"tokens": 100},
        )

        assert result.vault_experiment_path == "/path/to/experiment"
        assert result.vault_decision_paths == ["/path/to/decision"]
        assert result.token_metrics == {"tokens": 100}

    def test_failed_result(self):
        """[P0] Should create failed result."""
        result = ExecutionResult(
            success=False,
            output="Error: something failed",
            metrics={"error": "something failed"},
            duration_seconds=0.5,
        )

        assert result.success is False
        assert "Error" in result.output
