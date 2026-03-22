"""Tests for BatchableExecutor batch performance logging - Phase 3.1 Task #2."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from cohezion.compound.batch_executor import BatchableExecutor
from cohezion.compound.executor import CompoundExecutor
from cohezion.core.mcp_client import MCPClient, MCPToolError


@pytest.fixture
def mock_executor() -> CompoundExecutor:
    """Create a mock CompoundExecutor."""
    return Mock(spec=CompoundExecutor)


@pytest.fixture
def mock_mcp_client() -> MCPClient:
    """Create a mock MCPClient."""
    return Mock(spec=MCPClient)


@pytest.fixture
def batch_executor(mock_executor, mock_mcp_client) -> BatchableExecutor:
    """Create a BatchableExecutor with mocks."""
    return BatchableExecutor(
        executor=mock_executor,
        mcp_client=mock_mcp_client,
        batch_size=8,
        enable_deduplication=True,
        enable_adaptive_batch_sizing=True,
    )


class TestBatchPerformanceLogging:
    """Test batch performance logging functionality."""

    def test_log_batch_performance_successful(self, batch_executor, mock_mcp_client):
        """Test successful batch performance logging."""
        mock_mcp_client.vault_log_experiment = Mock(
            return_value="experiments/batch_performance_size8_4tasks_2026-02-08.md"
        )

        result = batch_executor._log_batch_performance(
            batch_size=8,
            task_count=4,
            throughput=320.5,
            cache_hit_rate=75.0,
            execution_time=5.0,
            tasks_failed=0,
            tasks_executed=4,
        )

        assert result == 1
        mock_mcp_client.vault_log_experiment.assert_called_once()

        # Verify the call parameters
        call_args = mock_mcp_client.vault_log_experiment.call_args
        assert call_args.kwargs["project"] == "cohezion"
        assert "batch_size=8" in call_args.kwargs["hypothesis"]
        assert "task_count=4" in call_args.kwargs["hypothesis"]
        assert "320" in call_args.kwargs["result"]  # throughput in result
        assert "75" in call_args.kwargs["result"]  # cache hit rate

    def test_log_batch_performance_no_mcp_client(self):
        """Test logging when no MCPClient configured."""
        executor = Mock(spec=CompoundExecutor)
        batch_exec = BatchableExecutor(
            executor=executor,
            mcp_client=None,
            batch_size=8,
        )

        result = batch_exec._log_batch_performance(
            batch_size=8,
            task_count=4,
            throughput=320.0,
            cache_hit_rate=75.0,
            execution_time=5.0,
            tasks_failed=0,
            tasks_executed=4,
        )

        assert result == 0

    def test_log_batch_performance_mcp_tool_error(self, batch_executor, mock_mcp_client):
        """Test logging when vault is unavailable (MCPToolError)."""
        mock_mcp_client.vault_log_experiment = Mock(side_effect=MCPToolError("Vault connection failed"))

        result = batch_executor._log_batch_performance(
            batch_size=8,
            task_count=4,
            throughput=320.0,
            cache_hit_rate=75.0,
            execution_time=5.0,
            tasks_failed=0,
            tasks_executed=4,
        )

        assert result == 0

    def test_log_batch_performance_generic_exception(self, batch_executor, mock_mcp_client):
        """Test logging handles generic exceptions gracefully."""
        mock_mcp_client.vault_log_experiment = Mock(side_effect=Exception("Unexpected error"))

        result = batch_executor._log_batch_performance(
            batch_size=8,
            task_count=4,
            throughput=320.0,
            cache_hit_rate=75.0,
            execution_time=5.0,
            tasks_failed=0,
            tasks_executed=4,
        )

        assert result == 0

    def test_log_batch_performance_includes_all_metrics(self, batch_executor, mock_mcp_client):
        """Test that logging includes all performance metrics."""
        mock_mcp_client.vault_log_experiment = Mock(return_value="experiments/batch_perf.md")

        batch_executor._log_batch_performance(
            batch_size=16,
            task_count=10,
            throughput=450.75,
            cache_hit_rate=82.5,
            execution_time=3.25,
            tasks_failed=1,
            tasks_executed=9,
        )

        call_args = mock_mcp_client.vault_log_experiment.call_args
        result_text = call_args.kwargs["result"]

        # Verify all metrics appear in result
        assert "450" in result_text  # throughput
        assert "82" in result_text  # cache hit rate
        assert "3.25" in result_text  # execution time
        assert "9" in result_text  # tasks executed
        assert "1" in result_text  # tasks failed

    def test_log_batch_performance_calculates_success_rate(self, batch_executor, mock_mcp_client):
        """Test that success rate is calculated correctly."""
        mock_mcp_client.vault_log_experiment = Mock(return_value="experiments/batch_perf.md")

        batch_executor._log_batch_performance(
            batch_size=8,
            task_count=10,
            throughput=300.0,
            cache_hit_rate=70.0,
            execution_time=4.0,
            tasks_failed=2,
            tasks_executed=8,
        )

        call_args = mock_mcp_client.vault_log_experiment.call_args
        learnings_text = call_args.kwargs["learnings"]

        # Success rate should be 80% (8/10)
        assert "80" in learnings_text

    def test_log_batch_performance_hypothesis_format(self, batch_executor, mock_mcp_client):
        """Test hypothesis has correct format."""
        mock_mcp_client.vault_log_experiment = Mock(return_value="experiments/batch_perf.md")

        batch_executor._log_batch_performance(
            batch_size=32,
            task_count=20,
            throughput=400.0,
            cache_hit_rate=80.0,
            execution_time=6.0,
            tasks_failed=0,
            tasks_executed=20,
        )

        call_args = mock_mcp_client.vault_log_experiment.call_args
        hypothesis = call_args.kwargs["hypothesis"]

        assert "batch_size=32" in hypothesis
        assert "task_count=20" in hypothesis

    def test_log_batch_performance_method_format(self, batch_executor, mock_mcp_client):
        """Test method description includes configuration."""
        mock_mcp_client.vault_log_experiment = Mock(return_value="experiments/batch_perf.md")

        batch_executor._log_batch_performance(
            batch_size=8,
            task_count=5,
            throughput=300.0,
            cache_hit_rate=75.0,
            execution_time=2.5,
            tasks_failed=0,
            tasks_executed=5,
        )

        call_args = mock_mcp_client.vault_log_experiment.call_args
        method = call_args.kwargs["method"]

        # Should include deduplication and adaptive sizing settings
        assert "deduplication=True" in method
        assert "adaptive_sizing=True" in method

    def test_log_batch_performance_title_format(self, batch_executor, mock_mcp_client):
        """Test title format for vault experiment."""
        mock_mcp_client.vault_log_experiment = Mock(return_value="experiments/batch_perf.md")

        batch_executor._log_batch_performance(
            batch_size=16,
            task_count=8,
            throughput=350.0,
            cache_hit_rate=80.0,
            execution_time=3.5,
            tasks_failed=0,
            tasks_executed=8,
        )

        call_args = mock_mcp_client.vault_log_experiment.call_args
        title = call_args.kwargs["title"]

        # Title should reference batch size and task count
        assert "batch" in title.lower()
        assert "16" in title
        assert "8" in title

    def test_log_batch_performance_zero_throughput(self, batch_executor, mock_mcp_client):
        """Test logging with zero throughput (edge case)."""
        mock_mcp_client.vault_log_experiment = Mock(return_value="experiments/batch_perf.md")

        result = batch_executor._log_batch_performance(
            batch_size=8,
            task_count=4,
            throughput=0.0,  # Zero throughput
            cache_hit_rate=0.0,
            execution_time=0.1,
            tasks_failed=4,
            tasks_executed=0,
        )

        assert result == 1
        mock_mcp_client.vault_log_experiment.assert_called_once()

    def test_log_batch_performance_perfect_execution(self, batch_executor, mock_mcp_client):
        """Test logging with perfect metrics."""
        mock_mcp_client.vault_log_experiment = Mock(return_value="experiments/batch_perf.md")

        result = batch_executor._log_batch_performance(
            batch_size=8,
            task_count=8,
            throughput=500.0,
            cache_hit_rate=100.0,
            execution_time=2.0,
            tasks_failed=0,
            tasks_executed=8,
        )

        assert result == 1
        call_args = mock_mcp_client.vault_log_experiment.call_args
        result_text = call_args.kwargs["result"]

        # Should show perfect success rate
        assert "8/8" in result_text  # All tasks executed

    def test_log_batch_performance_high_failure_rate(self, batch_executor, mock_mcp_client):
        """Test logging with high failure rate."""
        mock_mcp_client.vault_log_experiment = Mock(return_value="experiments/batch_perf.md")

        result = batch_executor._log_batch_performance(
            batch_size=8,
            task_count=10,
            throughput=100.0,
            cache_hit_rate=30.0,
            execution_time=8.0,
            tasks_failed=7,
            tasks_executed=3,
        )

        assert result == 1
        call_args = mock_mcp_client.vault_log_experiment.call_args
        result_text = call_args.kwargs["result"]

        # Should show high failure count
        assert "7" in result_text  # Failures

    def test_log_batch_performance_float_precision(self, batch_executor, mock_mcp_client):
        """Test that throughput and timing have appropriate precision."""
        mock_mcp_client.vault_log_experiment = Mock(return_value="experiments/batch_perf.md")

        batch_executor._log_batch_performance(
            batch_size=8,
            task_count=4,
            throughput=333.33333,
            cache_hit_rate=66.66666,
            execution_time=1.2345,
            tasks_failed=0,
            tasks_executed=4,
        )

        call_args = mock_mcp_client.vault_log_experiment.call_args
        result_text = call_args.kwargs["result"]

        # Throughput should be formatted to 1 decimal
        assert "333.3" in result_text
        # Execution time should be formatted to 2 decimals
        assert "1.23" in result_text

    def test_log_batch_performance_vault_project_is_cohezion(self, batch_executor, mock_mcp_client):
        """Test that vault project is always 'cohezion'."""
        mock_mcp_client.vault_log_experiment = Mock(return_value="experiments/batch_perf.md")

        batch_executor._log_batch_performance(
            batch_size=8,
            task_count=4,
            throughput=320.0,
            cache_hit_rate=75.0,
            execution_time=5.0,
            tasks_failed=0,
            tasks_executed=4,
        )

        call_args = mock_mcp_client.vault_log_experiment.call_args
        assert call_args.kwargs["project"] == "cohezion"

    def test_log_batch_performance_return_values(self, batch_executor, mock_mcp_client):
        """Test return values for different scenarios."""
        # Success case
        mock_mcp_client.vault_log_experiment = Mock(return_value="experiments/batch_perf.md")
        result = batch_executor._log_batch_performance(
            batch_size=8,
            task_count=4,
            throughput=320.0,
            cache_hit_rate=75.0,
            execution_time=5.0,
            tasks_failed=0,
            tasks_executed=4,
        )
        assert result == 1

        # Failure case
        mock_mcp_client.vault_log_experiment = Mock(side_effect=Exception("Error"))
        result = batch_executor._log_batch_performance(
            batch_size=8,
            task_count=4,
            throughput=320.0,
            cache_hit_rate=75.0,
            execution_time=5.0,
            tasks_failed=0,
            tasks_executed=4,
        )
        assert result == 0
