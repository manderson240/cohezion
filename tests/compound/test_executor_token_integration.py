"""Tests for CompoundExecutor integration with TokenEfficientClient."""

from unittest.mock import MagicMock, patch

import pytest

from cohezion.compound.executor import (
    CompoundExecutor,
    ExecutionResult,
    ExecutorFactory,
)


@pytest.fixture
def mock_mcp_client():
    """Create mock MCP client."""
    return MagicMock()


@pytest.fixture
def mock_token_client():
    """Create mock TokenEfficientClient."""
    client = MagicMock()
    client.get_metrics.return_value = {
        "cache_hit_rate": 0.5,
        "cache_hits": 10,
        "cache_misses": 10,
        "total_tokens": 1000,
        "api_calls": 5,
        "estimated_tokens_saved": 1500,
    }
    return client


@pytest.fixture
def executor(mock_mcp_client):
    """Create compound executor without token client."""
    with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
        return CompoundExecutor(mock_mcp_client)


@pytest.fixture
def executor_with_token_client(mock_mcp_client, mock_token_client):
    """Create compound executor with token client."""
    with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
        return CompoundExecutor(mock_mcp_client, mock_token_client)


class TestCompoundExecutorTokenIntegration:
    """Tests for TokenEfficientClient integration."""

    def setup_method(self):
        ExecutorFactory.reset_singleton()

    def teardown_method(self):
        ExecutorFactory.reset_singleton()

    def test_executor_initialization_without_token_client(self, mock_mcp_client):
        """Test executor initialization without token client."""
        with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
            executor = CompoundExecutor(mock_mcp_client)
            assert executor.token_client is None
            assert executor.mcp_client == mock_mcp_client

    def test_executor_initialization_with_token_client(self, mock_mcp_client, mock_token_client):
        """Test executor initialization with token client."""
        with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
            executor = CompoundExecutor(mock_mcp_client, mock_token_client)
            assert executor.token_client == mock_token_client
            assert executor.mcp_client == mock_mcp_client

    def test_execute_task_without_token_client(self, executor):
        """Test task execution without token client."""
        with (
            patch.object(
                executor.logger,
                "get_experience_guidance",
                return_value={"context": "test"},
            ),
            patch.object(executor.logger, "log_execution_start", return_value="exp_path"),
            patch.object(executor.logger, "log_execution_result") as mock_log_result,
            patch.object(executor.logger, "extract_execution_pattern", return_value="pattern_path"),
        ):

            def execute_fn(guidance):
                return "output", {"key": "value"}

            result = executor.execute_task(
                task_description="Test task",
                skill_name="test_skill",
                operation_type="generate",
                execute_fn=execute_fn,
            )

            assert result.success
            assert result.output == "output"
            assert result.metrics["key"] == "value"
            assert result.token_metrics is None  # No token client
            mock_log_result.assert_called_once()

    def test_execute_task_with_token_client(self, executor_with_token_client):
        """Test task execution with token client."""
        mock_token_client = executor_with_token_client.token_client
        mock_token_client.get_metrics.side_effect = [
            {  # Before execution
                "cache_hit_rate": 0.4,
                "cache_hits": 5,
                "cache_misses": 10,
                "total_tokens": 500,
                "api_calls": 3,
            },
            {  # After execution
                "cache_hit_rate": 0.5,
                "cache_hits": 10,
                "cache_misses": 10,
                "total_tokens": 1000,
                "api_calls": 5,
            },
        ]

        with (
            patch.object(
                executor_with_token_client.logger,
                "get_experience_guidance",
                return_value={"context": "test"},
            ),
            patch.object(
                executor_with_token_client.logger,
                "log_execution_start",
                return_value="exp_path",
            ),
            patch.object(executor_with_token_client.logger, "log_execution_result"),
            patch.object(
                executor_with_token_client.logger,
                "extract_execution_pattern",
                return_value="pattern_path",
            ),
        ):

            def execute_fn(guidance):
                return "output", {"key": "value"}

            result = executor_with_token_client.execute_task(
                task_description="Test task",
                skill_name="test_skill",
                operation_type="generate",
                execute_fn=execute_fn,
            )

            assert result.success
            assert result.output == "output"
            assert result.token_metrics is not None
            assert result.token_metrics["tokens_used"] == 500  # 1000 - 500
            assert result.token_metrics["api_calls_made"] == 2  # 5 - 3
            assert result.token_metrics["cache_hits"] == 5  # 10 - 5
            assert result.token_metrics["cache_misses"] == 0  # 10 - 10
            assert result.token_metrics["cache_hit_rate"] == 0.5

    def test_token_metrics_computation(self, executor_with_token_client):
        """Test token metrics delta computation."""
        before = {
            "total_tokens": 1000,
            "api_calls": 5,
            "cache_hits": 10,
            "cache_misses": 10,
            "cache_hit_rate": 0.5,
        }
        after = {
            "total_tokens": 1500,
            "api_calls": 7,
            "cache_hits": 15,
            "cache_misses": 12,
            "cache_hit_rate": 0.55,
        }

        delta = executor_with_token_client._compute_token_delta(before, after)

        assert delta["tokens_used"] == 500  # 1500 - 1000
        assert delta["api_calls_made"] == 2  # 7 - 5
        assert delta["cache_hits"] == 5  # 15 - 10
        assert delta["cache_misses"] == 2  # 12 - 10
        assert delta["cache_hit_rate"] == 0.55

    def test_token_metrics_first_execution(self, executor_with_token_client):
        """Test token metrics on first execution (no before metrics)."""
        after = {
            "total_tokens": 1000,
            "api_calls": 5,
            "cache_hits": 10,
            "cache_misses": 10,
            "cache_hit_rate": 0.5,
        }

        delta = executor_with_token_client._compute_token_delta(None, after)

        # When no before metrics, delta should equal after metrics
        assert delta == after

    def test_execute_task_with_error_and_token_client(self, executor_with_token_client):
        """Test error handling with token client."""
        mock_token_client = executor_with_token_client.token_client
        mock_token_client.get_metrics.side_effect = [
            {
                "cache_hit_rate": 0.4,
                "cache_hits": 5,
                "cache_misses": 10,
                "total_tokens": 500,
                "api_calls": 3,
            },
            {
                "cache_hit_rate": 0.4,
                "cache_hits": 5,
                "cache_misses": 10,
                "total_tokens": 700,
                "api_calls": 4,
            },
        ]

        with (
            patch.object(
                executor_with_token_client.logger,
                "get_experience_guidance",
                return_value={"context": "test"},
            ),
            patch.object(
                executor_with_token_client.logger,
                "log_execution_start",
                return_value="exp_path",
            ),
            patch.object(executor_with_token_client.logger, "log_execution_result"),
        ):

            def execute_fn(guidance):
                raise ValueError("Execution failed")

            result = executor_with_token_client.execute_task(
                task_description="Failing task",
                skill_name="test_skill",
                operation_type="generate",
                execute_fn=execute_fn,
            )

            assert not result.success
            assert "Error" in result.output
            # Token metrics should still be captured even on error
            assert result.token_metrics is not None
            assert result.token_metrics["tokens_used"] == 200  # 700 - 500

    def test_execution_result_token_metrics_field(self):
        """Test ExecutionResult has token_metrics field."""
        result = ExecutionResult(
            success=True,
            output="test",
            metrics={"key": "value"},
            duration_seconds=1.0,
            token_metrics={"tokens_used": 100, "cache_hits": 5},
        )

        assert result.token_metrics is not None
        assert result.token_metrics["tokens_used"] == 100
        assert result.token_metrics["cache_hits"] == 5

    def test_execution_result_token_metrics_optional(self):
        """Test ExecutionResult token_metrics is optional."""
        result = ExecutionResult(
            success=True,
            output="test",
            metrics={"key": "value"},
            duration_seconds=1.0,
        )

        assert result.token_metrics is None


class TestExecutorFactory:
    """Tests for ExecutorFactory."""

    def test_factory_create_without_token_client(self, mock_mcp_client):
        """Test factory create without token client."""
        with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
            executor = ExecutorFactory.create(mock_mcp_client)
            assert executor is not None
            assert executor.token_client is None

    def test_factory_create_with_token_client(self, mock_mcp_client, mock_token_client):
        """Test factory create with token client."""
        with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
            executor = ExecutorFactory.create(mock_mcp_client, mock_token_client)
            assert executor is not None
            assert executor.token_client == mock_token_client

    def test_factory_singleton_without_token_client(self, mock_mcp_client):
        """Test factory singleton without token client."""
        with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
            ExecutorFactory.reset_singleton()
            executor1 = ExecutorFactory.get_singleton(mock_mcp_client)
            executor2 = ExecutorFactory.get_singleton(mock_mcp_client)
            assert executor1 is executor2
            ExecutorFactory.reset_singleton()

    def test_factory_singleton_with_token_client(self, mock_mcp_client, mock_token_client):
        """Test factory singleton with token client."""
        with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
            ExecutorFactory.reset_singleton()
            executor1 = ExecutorFactory.get_singleton(mock_mcp_client, mock_token_client)
            executor2 = ExecutorFactory.get_singleton(mock_mcp_client)
            assert executor1 is executor2
            assert executor1.token_client == mock_token_client
            ExecutorFactory.reset_singleton()

    def test_factory_reset_singleton(self, mock_mcp_client):
        """Test factory reset singleton."""
        with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
            ExecutorFactory.reset_singleton()
            ExecutorFactory.get_singleton(mock_mcp_client)
            assert ExecutorFactory._instance is not None
            ExecutorFactory.reset_singleton()
            assert ExecutorFactory._instance is None


class TestCompoundExecutorIntegrationScenarios:
    """Integration scenarios with token client."""

    def setup_method(self):
        ExecutorFactory.reset_singleton()

    def teardown_method(self):
        ExecutorFactory.reset_singleton()

    def test_batch_generation_with_token_efficiency(self, executor_with_token_client):
        """Test batch generation scenario with token efficiency."""
        mock_token_client = executor_with_token_client.token_client

        # Simulate batch processing: first call gets metrics before, second after
        mock_token_client.get_metrics.side_effect = [
            {  # Before: 100 items processed
                "cache_hit_rate": 0.3,
                "cache_hits": 30,
                "cache_misses": 70,
                "total_tokens": 5000,
                "api_calls": 70,
            },
            {  # After: 110 items processed
                "cache_hit_rate": 0.45,  # Better hit rate
                "cache_hits": 50,  # 20 new hits
                "cache_misses": 80,  # 10 new misses
                "total_tokens": 6500,  # 1500 tokens used
                "api_calls": 80,  # 10 new API calls
            },
        ]

        with (
            patch.object(
                executor_with_token_client.logger,
                "get_experience_guidance",
                return_value={"similar_tasks": ["task_1", "task_2"]},
            ),
            patch.object(
                executor_with_token_client.logger,
                "log_execution_start",
                return_value="batch_exp_path",
            ),
            patch.object(executor_with_token_client.logger, "log_execution_result"),
            patch.object(
                executor_with_token_client.logger,
                "extract_execution_pattern",
                return_value="batch_pattern_path",
            ),
        ):

            def batch_execute(guidance):
                # Simulate batch generation
                outputs = ["result_1", "result_2", "result_3"]
                return "\n".join(outputs), {
                    "batch_size": 10,
                    "success_rate": 1.0,
                }

            result = executor_with_token_client.execute_task(
                task_description="Batch generate 10 items with caching",
                skill_name="batch_generator",
                operation_type="generate",
                execute_fn=batch_execute,
            )

            assert result.success
            assert result.token_metrics is not None
            assert result.token_metrics["tokens_used"] == 1500
            assert result.token_metrics["api_calls_made"] == 10
            assert result.token_metrics["cache_hits"] == 20
            assert result.token_metrics["cache_hit_rate"] == 0.45
