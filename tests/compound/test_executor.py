"""Tests for compound executor with vault integration."""

import json
from unittest.mock import MagicMock, patch

import pytest

from cohezion.compound.executor import CompoundExecutor, ExecutorFactory, ExecutionResult


@pytest.fixture
def mock_mcp_client():
    """Create a mock MCP client."""
    client = MagicMock()
    client.vault_find_relevant_context.return_value = [
        {"file": "experiments/similar.md", "score": 0.85}
    ]
    client.vault_log_experiment.return_value = "experiments/execution_123.md"
    client.vault_log_decision.return_value = "decisions/inflection_456.md"
    client.vault_extract_pattern.return_value = "patterns/success_789.md"
    client.vault_edit.return_value = "success"
    return client


@pytest.fixture
def executor(mock_mcp_client):
    """Create a test executor."""
    return CompoundExecutor(mock_mcp_client)


def test_executor_init(mock_mcp_client):
    """Test executor initialization."""
    executor = CompoundExecutor(mock_mcp_client)
    assert executor.mcp_client == mock_mcp_client
    assert executor.logger is not None


def test_get_experience_guidance(executor, mock_mcp_client):
    """Test fetching experience guidance."""
    guidance = executor.get_experience_guidance(
        task_description="Optimize token usage",
        project="cohezion",
    )

    assert "relevant_context" in guidance
    mock_mcp_client.vault_find_relevant_context.assert_called_once()


def test_execute_task_success(executor, mock_mcp_client):
    """Test successful task execution."""

    def dummy_task(guidance):
        return "Task output", {"tokens": 100, "latency": 1.5}

    result = executor.execute_task(
        task_description="Test task",
        skill_name="test_skill",
        operation_type="generate",
        execute_fn=dummy_task,
    )

    assert result.success is True
    assert result.output == "Task output"
    assert result.metrics["tokens"] == 100
    assert result.vault_experiment_path == "experiments/execution_123.md"
    assert result.vault_decision_paths is not None
    assert len(result.vault_decision_paths) > 0


def test_execute_task_failure(executor, mock_mcp_client):
    """Test task execution with failure."""

    def failing_task(guidance):
        raise ValueError("Task failed")

    result = executor.execute_task(
        task_description="Failing task",
        skill_name="test_skill",
        operation_type="analyze",
        execute_fn=failing_task,
    )

    assert result.success is False
    assert "Error: Task failed" in result.output
    assert "error" in result.metrics
    # Execution is still logged even on failure
    mock_mcp_client.vault_edit.assert_called()


def test_execute_task_includes_guidance(executor):
    """Test that execute_fn receives experience guidance."""
    received_guidance = None

    def capture_guidance(guidance):
        nonlocal received_guidance
        received_guidance = guidance
        return "output", {}

    executor.execute_task(
        task_description="Test",
        skill_name="test",
        operation_type="generate",
        execute_fn=capture_guidance,
    )

    assert received_guidance is not None
    assert "relevant_context" in received_guidance


def test_execute_task_logs_start_and_result(executor, mock_mcp_client):
    """Test that both start and result logging are called."""

    def dummy_task(guidance):
        return "result", {"metric": 1.0}

    executor.execute_task(
        task_description="Test",
        skill_name="test_skill",
        operation_type="transform",
        execute_fn=dummy_task,
    )

    # Should log start (1) and edit for result (1)
    assert mock_mcp_client.vault_log_experiment.called
    assert mock_mcp_client.vault_edit.called


def test_execute_task_extracts_pattern_on_success(executor, mock_mcp_client):
    """Test pattern extraction after successful execution."""

    def dummy_task(guidance):
        return "success", {"coherence": 0.92}

    result = executor.execute_task(
        task_description="Pattern extraction test",
        skill_name="pattern_skill",
        operation_type="generate",
        execute_fn=dummy_task,
    )

    assert result.success is True
    mock_mcp_client.vault_extract_pattern.assert_called_once()

    # Verify pattern call arguments
    call_kwargs = mock_mcp_client.vault_extract_pattern.call_args[1]
    assert "pattern_skill" in call_kwargs["pattern_name"]
    assert "generate" in call_kwargs["pattern_name"]
    assert call_kwargs["domain"] == "compound-engineering"


def test_execute_task_no_pattern_on_failure(executor, mock_mcp_client):
    """Test that patterns are not extracted on failure."""

    def failing_task(guidance):
        raise RuntimeError("Failed")

    result = executor.execute_task(
        task_description="Failing task",
        skill_name="test",
        operation_type="analyze",
        execute_fn=failing_task,
    )

    assert result.success is False
    # Pattern extraction should not be called on failure
    mock_mcp_client.vault_extract_pattern.assert_not_called()


def test_log_inflection_point(executor, mock_mcp_client):
    """Test logging inflection points."""
    path = executor.log_inflection_point(
        title="Critical threshold",
        context="Token budget exceeded",
        decision="Switch to smaller model",
        rationale="Maintain quality",
    )

    assert path == "decisions/inflection_456.md"
    mock_mcp_client.vault_log_decision.assert_called_once()


def test_execution_result_dataclass(executor):
    """Test ExecutionResult dataclass."""

    def dummy_task(guidance):
        return "output", {"metric": 1.0}

    result = executor.execute_task(
        task_description="Test",
        skill_name="test",
        operation_type="generate",
        execute_fn=dummy_task,
    )

    assert isinstance(result, ExecutionResult)
    assert result.success is True
    assert result.duration_seconds >= 0
    assert result.vault_decision_paths is not None


def test_executor_factory_create(mock_mcp_client):
    """Test factory creation."""
    executor = ExecutorFactory.create(mock_mcp_client)
    assert isinstance(executor, CompoundExecutor)
    assert executor.mcp_client == mock_mcp_client


def test_executor_factory_singleton(mock_mcp_client):
    """Test singleton pattern."""
    ExecutorFactory.reset_singleton()

    executor1 = ExecutorFactory.get_singleton(mock_mcp_client)
    executor2 = ExecutorFactory.get_singleton(mock_mcp_client)

    assert executor1 is executor2

    ExecutorFactory.reset_singleton()


def test_execute_task_duration(executor):
    """Test that duration is measured correctly."""
    import time

    def slow_task(guidance):
        time.sleep(0.1)
        return "output", {}

    result = executor.execute_task(
        task_description="Slow task",
        skill_name="slow",
        operation_type="generate",
        execute_fn=slow_task,
    )

    assert result.duration_seconds >= 0.1


def test_execute_task_with_custom_project(executor, mock_mcp_client):
    """Test execution with custom project name."""

    def dummy_task(guidance):
        return "output", {}

    executor.execute_task(
        task_description="Test",
        skill_name="test",
        operation_type="generate",
        execute_fn=dummy_task,
        project="custom_project",
    )

    # Verify project name was passed to vault logging
    call_kwargs = mock_mcp_client.vault_log_experiment.call_args[1]
    assert call_kwargs["project"] == "custom_project"
