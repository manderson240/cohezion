"""Tests for vault execution logging in compound engineering."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from cohezion.compound.vault_execution_logger import (
    ExecutionContext,
    VaultExecutionLogger,
)


@pytest.fixture
def mock_mcp_client():
    """Create a mock MCP client."""
    client = MagicMock()
    client.vault_find_relevant_context.return_value = [
        {"file": "experiments/2026-02-08-similar-task.md", "excerpt": "..."}
    ]
    client.vault_log_experiment.return_value = "experiments/test_execution.md"
    client.vault_log_decision.return_value = "decisions/test_decision.md"
    client.vault_extract_pattern.return_value = "patterns/test_pattern.md"
    client.vault_edit.return_value = "success"
    return client


@pytest.fixture
def execution_context(mock_mcp_client):
    """Create a test execution context."""
    return ExecutionContext(
        project="cohezion",
        skill_name="test_skill",
        task_description="Test compound execution",
        operation_type="generate",
        start_time=datetime.now(),
        mcp_client=mock_mcp_client,
    )


def test_vault_execution_logger_init(mock_mcp_client):
    """Test logger initialization."""
    logger = VaultExecutionLogger(mock_mcp_client)
    assert logger.mcp_client == mock_mcp_client


def test_get_experience_guidance(mock_mcp_client):
    """Test fetching experience guidance from vault."""
    logger = VaultExecutionLogger(mock_mcp_client)

    guidance = logger.get_experience_guidance(
        task_description="Similar task", project="cohezion"
    )

    assert "relevant_context" in guidance
    assert len(guidance["relevant_context"]) > 0
    mock_mcp_client.vault_find_relevant_context.assert_called_once()


def test_get_experience_guidance_error_handling(mock_mcp_client):
    """Test error handling when vault is unavailable."""
    mock_mcp_client.vault_find_relevant_context.side_effect = ConnectionError(
        "Vault unavailable"
    )

    logger = VaultExecutionLogger(mock_mcp_client)
    guidance = logger.get_experience_guidance(
        task_description="Test", project="cohezion"
    )

    assert "error" in guidance
    assert guidance["error"] == "Vault unavailable"


def test_log_execution_start(mock_mcp_client, execution_context):
    """Test logging execution start."""
    logger = VaultExecutionLogger(mock_mcp_client)

    result = logger.log_execution_start(execution_context)

    assert result == "experiments/test_execution.md"
    mock_mcp_client.vault_log_experiment.assert_called_once()

    # Verify call arguments
    call_kwargs = mock_mcp_client.vault_log_experiment.call_args[1]
    assert call_kwargs["project"] == "cohezion"
    assert "test_skill" in call_kwargs["hypothesis"]
    assert call_kwargs["result"] == ""  # Empty until execution completes


def test_log_execution_result(mock_mcp_client):
    """Test logging execution results."""
    logger = VaultExecutionLogger(mock_mcp_client)

    metrics = {"token_efficiency": 0.85, "latency": 1.2, "coherence": 0.92}
    logger.log_execution_result(
        experiment_path="experiments/test.md",
        success=True,
        output="Test output",
        metrics=metrics,
    )

    mock_mcp_client.vault_edit.assert_called_once()

    # Verify edit operations
    call_args = mock_mcp_client.vault_edit.call_args
    edits = call_args[1]["edits"]
    assert len(edits) == 2  # result and learnings


def test_log_execution_result_skips_empty_path(mock_mcp_client):
    """Test that empty path doesn't attempt vault write."""
    logger = VaultExecutionLogger(mock_mcp_client)

    logger.log_execution_result(
        experiment_path="",
        success=True,
        output="Test",
        metrics={},
    )

    mock_mcp_client.vault_edit.assert_not_called()


def test_log_decision_point(mock_mcp_client):
    """Test logging a decision point."""
    logger = VaultExecutionLogger(mock_mcp_client)

    result = logger.log_decision_point(
        project="cohezion",
        title="Critical threshold reached",
        context="Token budget exceeded 80%",
        decision="Switch to smaller model",
        rationale="Maintain quality within token budget",
    )

    assert result == "decisions/test_decision.md"
    mock_mcp_client.vault_log_decision.assert_called_once()


def test_extract_execution_pattern(mock_mcp_client):
    """Test extracting reusable pattern from execution."""
    logger = VaultExecutionLogger(mock_mcp_client)

    result = logger.extract_execution_pattern(
        source_path="experiments/test.md",
        pattern_name="Efficient Token Usage",
        description="Pattern for managing token budget",
        domain="compound-engineering",
    )

    assert result == "patterns/test_pattern.md"
    mock_mcp_client.vault_extract_pattern.assert_called_once()


def test_vault_operations_log_errors(mock_mcp_client):
    """Test that vault operations handle errors gracefully."""
    mock_mcp_client.vault_log_decision.side_effect = Exception("Vault error")

    logger = VaultExecutionLogger(mock_mcp_client)

    result = logger.log_decision_point(
        project="cohezion",
        title="Test",
        context="Test context",
        decision="Test decision",
        rationale="Test rationale",
    )

    assert result == ""  # Returns empty string on error


def test_execution_context_attributes(execution_context):
    """Test ExecutionContext dataclass."""
    assert execution_context.project == "cohezion"
    assert execution_context.skill_name == "test_skill"
    assert execution_context.operation_type == "generate"
    assert isinstance(execution_context.start_time, datetime)
