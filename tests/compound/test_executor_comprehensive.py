"""Comprehensive tests for NEW simplified compound executor.

Tests the clean, focused 200-line implementation.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from cohezion.compound.core.executor import CompoundExecutor, ExecutionConfig
from cohezion.compound.models import ExecutionMetrics, ExecutionResult, Task


class TestCompoundExecutorInitialization:
    """[P0] Tests for new executor initialization."""

    def test_executor_initializes_minimal(self):
        """[P0] Should initialize with minimal dependencies."""

        def execute_fn(task, context):
            return ("output", {"total_tokens": 100})

        executor = CompoundExecutor(execute_fn=execute_fn)

        assert executor.execute_fn == execute_fn
        assert executor.config is not None

    def test_executor_initializes_with_config(self):
        """[P0] Should initialize with custom config."""

        def execute_fn(task, context):
            return ("output", {})

        config = ExecutionConfig(max_retries=5)
        executor = CompoundExecutor(execute_fn=execute_fn, config=config)

        assert executor.config.max_retries == 5

    def test_executor_initializes_with_analyzer(self):
        """[P0] Should initialize with analyzer."""

        def execute_fn(task, context):
            return ("output", {})

        analyzer = Mock()
        executor = CompoundExecutor(
            execute_fn=execute_fn,
            analyzer=analyzer,
        )

        assert executor.analyzer == analyzer


class TestCompoundExecutorExecution:
    """[P0] Tests for task execution."""

    @pytest.fixture()
    def executor(self):
        """Create executor with mock function."""

        def execute_fn(task, context):
            return (f"output for {task.description}", {"total_tokens": 100})

        return CompoundExecutor(execute_fn=execute_fn)

    @pytest.fixture()
    def task(self):
        """Create test task."""
        return Task(
            id="test-1",
            description="Test task",
            skill_name="test-skill",
            operation_type="generate",
        )

    def test_execute_task_successful(self, executor, task):
        """[P0] Should execute task successfully."""
        result = executor.execute(task)

        assert isinstance(result, ExecutionResult)
        assert result.success is True
        assert "Test task" in result.output

    def test_execute_task_with_metrics(self, executor, task):
        """[P0] Should capture metrics."""
        result = executor.execute(task)

        assert result.metrics.total_tokens == 100
        assert result.metrics.duration_seconds > 0

    def test_execute_task_with_failure(self, task):
        """[P0] Should handle task execution failure."""

        def failing_fn(task, context):
            raise ValueError("Test error")

        executor = CompoundExecutor(execute_fn=failing_fn)
        result = executor.execute(task)

        assert isinstance(result, ExecutionResult)
        assert result.success is False
        assert "Test error" in result.output

    def test_execute_task_records_duration(self, executor, task):
        """[P1] Should record execution duration."""
        result = executor.execute(task)

        assert result.metrics.duration_seconds > 0

    def test_execute_task_with_retry(self, task):
        """[P0] Should retry on failure."""
        attempts = []

        def flaky_fn(task, context):
            attempts.append(context.attempt_number)
            if context.attempt_number < 2:
                raise ValueError("Retry me")
            return ("success", {})

        executor = CompoundExecutor(
            execute_fn=flaky_fn,
            config=ExecutionConfig(max_retries=3),
        )
        result = executor.execute(task)

        assert result.success is True
        assert len(attempts) == 3  # Initial + 2 retries

    def test_execute_task_max_retries_exhausted(self, task):
        """[P0] Should fail after max retries."""

        def always_fails(task, context):
            raise ValueError("Always fails")

        executor = CompoundExecutor(
            execute_fn=always_fails,
            config=ExecutionConfig(max_retries=2),
        )
        result = executor.execute(task)

        assert result.success is False
        assert "Always fails" in result.output


class TestCompoundExecutorPlugins:
    """[P1] Tests for plugin system."""

    @pytest.fixture()
    def task(self):
        return Task(
            id="test-1",
            description="Test task",
            skill_name="test-skill",
            operation_type="generate",
        )

    def test_analyzer_called(self, task):
        """[P1] Should call analyzer after execution."""

        def execute_fn(task, context):
            return ("output", {})

        analyzer = Mock()
        analyzer.return_value = Mock(
            has_issues=lambda: False,
            retry_recommended=False,
        )

        executor = CompoundExecutor(
            execute_fn=execute_fn,
            analyzer=analyzer,
            config=ExecutionConfig(enable_analysis=True),
        )

        result = executor.execute(task)

        analyzer.assert_called_once()

    def test_analyzer_recommends_retry(self, task):
        """[P1] Should retry when analyzer recommends."""
        attempts = []

        def execute_fn(task, context):
            attempts.append(1)
            return ("output", {})

        analyzer = Mock()
        # First call recommends retry, second doesn't
        analyzer.side_effect = [
            Mock(has_issues=lambda: True, retry_recommended=True),
            Mock(has_issues=lambda: False, retry_recommended=False),
        ]

        executor = CompoundExecutor(
            execute_fn=execute_fn,
            analyzer=analyzer,
            config=ExecutionConfig(enable_analysis=True),
        )

        result = executor.execute(task)

        assert result.success is True
        assert len(attempts) == 2  # Retried once

    def test_persister_called(self, task):
        """[P1] Should call persister after execution."""

        def execute_fn(task, context):
            return ("output", {})

        persister = Mock()

        executor = CompoundExecutor(
            execute_fn=execute_fn,
            persister=persister,
            config=ExecutionConfig(enable_checkpointing=True),
        )

        result = executor.execute(task)

        persister.assert_called_once()


class TestExecutionResult:
    """[P0] Tests for ExecutionResult dataclass."""

    def test_result_creation(self):
        """[P0] Should create ExecutionResult."""
        result = ExecutionResult(
            success=True,
            output="test output",
            metrics=ExecutionMetrics(total_tokens=100),
        )

        assert result.success is True
        assert result.output == "test output"
        assert result.metrics.total_tokens == 100

    def test_result_failed_property(self):
        """[P0] Should have failed property."""
        result = ExecutionResult(
            success=False,
            output="error",
            metrics=ExecutionMetrics(),
        )

        assert result.failed is True

    def test_result_to_dict(self):
        """[P1] Should convert to dict."""
        result = ExecutionResult(
            success=True,
            output="test",
            metrics=ExecutionMetrics(total_tokens=50),
            vault_path="/path/to/vault",
        )

        data = result.to_dict()

        assert data["success"] is True
        assert data["output"] == "test"
        assert data["metrics"]["total_tokens"] == 50


class TestExecutionConfig:
    """[P1] Tests for ExecutionConfig."""

    def test_default_config(self):
        """[P1] Should have sensible defaults."""
        config = ExecutionConfig()

        assert config.max_retries == 3
        assert config.retry_delay_seconds == 1.0
        assert config.enable_analysis is True
        assert config.enable_checkpointing is True

    def test_custom_config(self):
        """[P1] Should accept custom values."""
        config = ExecutionConfig(
            max_retries=5,
            retry_delay_seconds=2.0,
            enable_analysis=False,
        )

        assert config.max_retries == 5
        assert config.retry_delay_seconds == 2.0
        assert config.enable_analysis is False


class TestExecuteSimple:
    """[P1] Tests for execute_simple convenience function."""

    def test_execute_simple_success(self):
        """[P1] Should execute simple task."""
        from cohezion.compound.core.executor import execute_simple

        result = execute_simple(
            task_description="Test",
            execute_fn=lambda: "output",
        )

        assert result.success is True
        assert result.output == "output"

    def test_execute_simple_failure(self):
        """[P1] Should handle simple failure."""
        from cohezion.compound.core.executor import execute_simple

        def failing_fn():
            raise ValueError("Failed")

        result = execute_simple(
            task_description="Test",
            execute_fn=failing_fn,
        )

        assert result.success is False
        assert "Failed" in result.output
