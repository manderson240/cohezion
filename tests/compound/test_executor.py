"""Tests for compound executor with vault integration."""

from unittest.mock import MagicMock

import pytest

from cohezion.compound.executor import (
    CompoundExecutor,
    ExecutionResult,
    ExecutorFactory,
)


@pytest.fixture
def mock_mcp_client():
    """Create a mock MCP client."""
    client = MagicMock()
    client.vault_find_relevant_context.return_value = [
        {"file": "experiments/similar.md", "score": 0.85}
    ]
    client.vault_search.return_value = [
        {"file": "experiments/similar.md", "score": 0.85}
    ]
    client.vault_write.return_value = "success"
    client.vault_read.return_value = '{"status": "started"}'
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
    mock_mcp_client.vault_search.assert_called_once()


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
    # VaultLogger generates path as experiments/{project}/{skill}/{timestamp}.json
    assert result.vault_experiment_path.startswith("experiments/cohezion/test_skill/")
    assert result.vault_experiment_path.endswith(".json")
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
    # Execution is still logged even on failure (via vault_write)
    assert mock_mcp_client.vault_write.call_count >= 2  # start + result


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

    # Should log start (vault_write) and result (vault_read + vault_write)
    # Plus pattern extraction (vault_write) = at least 3 vault_write calls
    assert mock_mcp_client.vault_write.call_count >= 2  # start + result
    assert mock_mcp_client.vault_read.called  # result reads first


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
    # Pattern extraction happens via vault_write
    # Calls: start + result + pattern = at least 3
    assert mock_mcp_client.vault_write.call_count >= 3

    # Verify pattern was written (check call args for pattern path)
    pattern_calls = [
        call for call in mock_mcp_client.vault_write.call_args_list
        if "patterns/domains/compound-engineering" in str(call)
    ]
    assert len(pattern_calls) >= 1


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
    # Pattern extraction should not happen on failure
    # Calls: start + result + inflection point (3 total)
    # Verify no pattern paths in calls (pattern extraction writes to patterns/domains/)
    pattern_calls = [
        call for call in mock_mcp_client.vault_write.call_args_list
        if "patterns/domains" in str(call)
    ]
    assert len(pattern_calls) == 0  # no pattern extraction on failure


def test_log_inflection_point(executor, mock_mcp_client):
    """Test logging inflection points."""
    path = executor.log_inflection_point(
        title="Critical threshold",
        context="Token budget exceeded",
        decision="Switch to smaller model",
        rationale="Maintain quality",
    )

    # Path should be decisions/{project}/inflection_{timestamp}.md
    assert path.startswith("decisions/cohezion/inflection_")
    assert path.endswith(".md")
    # Decision logging uses vault_write
    mock_mcp_client.vault_write.assert_called()


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

    result = executor.execute_task(
        task_description="Test",
        skill_name="test",
        operation_type="generate",
        execute_fn=dummy_task,
        project="custom_project",
    )

    # Verify project name appears in experiment path
    assert result.vault_experiment_path.startswith("experiments/custom_project/test/")
    # Vault logging uses vault_write, verify it was called
    assert mock_mcp_client.vault_write.call_count >= 1


def test_executor_guardrails_enabled_by_default(mock_mcp_client):
    """Test that guardrails are enabled by default."""
    executor = CompoundExecutor(mock_mcp_client)
    assert executor.guardrail_pipeline is not None


def test_executor_guardrails_can_be_disabled(mock_mcp_client):
    """Test that guardrails can be disabled."""
    executor = CompoundExecutor(mock_mcp_client, enable_guardrails=False)
    assert executor.guardrail_pipeline is None


def test_executor_custom_guardrail_pipeline(mock_mcp_client):
    """Test executor with custom guardrail pipeline."""
    from cohezion.security.guardrail_factory import create_minimal_pipeline

    custom_pipeline = create_minimal_pipeline()
    executor = CompoundExecutor(
        mock_mcp_client, guardrail_pipeline=custom_pipeline
    )
    assert executor.guardrail_pipeline == custom_pipeline


def test_execute_task_with_guardrails_enabled(mock_mcp_client):
    """Test task execution with guardrails enabled."""

    def dummy_task(guidance):
        return "safe output", {"result": "ok"}

    executor = CompoundExecutor(mock_mcp_client, enable_guardrails=True)
    result = executor.execute_task(
        task_description="Safe task",
        skill_name="test",
        operation_type="generate",
        execute_fn=dummy_task,
    )

    assert result.success is True
    assert result.output == "safe output"


def test_executor_factory_with_guardrails(mock_mcp_client):
    """Test factory creates executor with guardrails enabled."""
    executor = ExecutorFactory.create(
        mock_mcp_client, enable_guardrails=True
    )
    assert executor.guardrail_pipeline is not None


def test_executor_factory_without_guardrails(mock_mcp_client):
    """Test factory creates executor with guardrails disabled."""
    executor = ExecutorFactory.create(
        mock_mcp_client, enable_guardrails=False
    )
    assert executor.guardrail_pipeline is None


def test_executor_singleton_with_guardrails(mock_mcp_client):
    """Test singleton maintains guardrail configuration."""
    ExecutorFactory.reset_singleton()
    executor1 = ExecutorFactory.get_singleton(
        mock_mcp_client, enable_guardrails=True
    )
    executor2 = ExecutorFactory.get_singleton(mock_mcp_client)

    assert executor1 is executor2
    assert executor1.guardrail_pipeline is not None
