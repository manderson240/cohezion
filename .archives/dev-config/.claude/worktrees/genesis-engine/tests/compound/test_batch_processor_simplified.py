"""Comprehensive tests for compound batch processor.

Tests the clean, simplified batch processing implementation.
Generated for P0 coverage.
"""

from __future__ import annotations

import pytest

from cohezion.compound.core.batch_processor import (
    BatchConfig,
    BatchProcessor,
    BatchResult,
    SimpleBatch,
)
from cohezion.compound.models import ExecutionMetrics, ExecutionResult, Task


class TestBatchConfig:
    """[P0] Tests for BatchConfig."""

    def test_default_values(self):
        """[P0] Should have sensible defaults."""
        config = BatchConfig()

        assert config.max_batch_size == 10
        assert config.optimal_batch_size == 5
        assert config.max_wait_seconds == 30.0
        assert config.max_concurrent == 4

    def test_custom_config(self):
        """[P0] Should accept custom values."""
        config = BatchConfig(
            max_batch_size=20,
            optimal_batch_size=8,
            max_wait_seconds=60.0,
            max_concurrent=8,
        )

        assert config.max_batch_size == 20
        assert config.optimal_batch_size == 8
        assert config.max_wait_seconds == 60.0
        assert config.max_concurrent == 8

    def test_should_batch_true(self):
        """[P0] Should indicate batching when queue >= optimal."""
        config = BatchConfig(optimal_batch_size=5)

        assert config.should_batch(5) is True
        assert config.should_batch(10) is True

    def test_should_batch_false(self):
        """[P0] Should indicate no batching when queue < optimal."""
        config = BatchConfig(optimal_batch_size=5)

        assert config.should_batch(4) is False
        assert config.should_batch(0) is False


class TestBatchProcessorInitialization:
    """[P0] Tests for BatchProcessor initialization."""

    def test_initializes_with_executor(self):
        """[P0] Should initialize with executor function."""

        def mock_executor(task, context):
            return ExecutionResult(success=True, output="done")

        processor = BatchProcessor(executor=mock_executor)

        assert processor.executor == mock_executor
        assert processor.config is not None
        assert processor.get_queue_size() == 0

    def test_initializes_with_custom_config(self):
        """[P0] Should initialize with custom config."""
        config = BatchConfig(max_batch_size=15)
        processor = BatchProcessor(executor=lambda t, c: None, config=config)

        assert processor.config.max_batch_size == 15


class TestBatchProcessorQueue:
    """[P0] Tests for queue management."""

    @pytest.fixture()
    def processor(self):
        def mock_executor(task, context):
            return ExecutionResult(success=True, output="done")

        return BatchProcessor(executor=mock_executor)

    @pytest.fixture()
    def sample_task(self):
        return Task(
            id="task-1",
            description="Test task",
            skill_name="test-skill",
            operation_type="generate",
        )

    def test_add_task_increases_queue(self, processor, sample_task):
        """[P0] Should add task to queue."""
        processor.add_task(sample_task)

        assert processor.get_queue_size() == 1

    def test_add_multiple_tasks(self, processor, sample_task):
        """[P0] Should add multiple tasks."""
        processor.add_task(sample_task)
        processor.add_task(sample_task)
        processor.add_task(sample_task)

        assert processor.get_queue_size() == 3

    def test_clear_queue(self, processor, sample_task):
        """[P0] Should clear all tasks."""
        processor.add_task(sample_task)
        processor.add_task(sample_task)

        processor.clear_queue()

        assert processor.get_queue_size() == 0

    def test_should_execute_true(self, processor, sample_task):
        """[P0] Should indicate execution when optimal reached."""
        processor.config = BatchConfig(optimal_batch_size=2)

        processor.add_task(sample_task)
        processor.add_task(sample_task)

        assert processor.should_execute() is True

    def test_should_execute_false(self, processor, sample_task):
        """[P0] Should indicate no execution when below optimal."""
        processor.config = BatchConfig(optimal_batch_size=5)

        processor.add_task(sample_task)

        assert processor.should_execute() is False


class TestBatchProcessorExecution:
    """[P0] Tests for batch execution."""

    @pytest.fixture()
    def sample_task(self):
        return Task(
            id="task-1",
            description="Test task",
            skill_name="test-skill",
            operation_type="generate",
        )

    @pytest.mark.asyncio()
    async def test_process_single_task(self, sample_task):
        """[P0] Should process single task."""
        executed_tasks = []

        def mock_executor(task, context):
            executed_tasks.append(task.id)
            return ExecutionResult(success=True, output=f"done-{task.id}")

        processor = BatchProcessor(executor=mock_executor)
        processor.add_task(sample_task)

        result = await processor.process_batch()

        assert len(result.results) == 1
        assert result.results[0].success is True
        assert result.results[0].output == "done-task-1"

    @pytest.mark.asyncio()
    async def test_process_multiple_tasks(self, sample_task):
        """[P0] Should process multiple tasks."""
        task2 = Task(
            id="task-2",
            description="Task 2",
            skill_name="test-skill",
            operation_type="generate",
        )

        executed = []

        def mock_executor(task, context):
            executed.append(task.id)
            return ExecutionResult(success=True, output=f"done-{task.id}")

        processor = BatchProcessor(executor=mock_executor)
        processor.add_task(sample_task)
        processor.add_task(task2)

        result = await processor.process_batch()

        assert len(result.results) == 2
        assert "task-1" in executed
        assert "task-2" in executed

    @pytest.mark.asyncio()
    async def test_process_empty_queue(self):
        """[P0] Should handle empty queue."""
        processor = BatchProcessor(executor=lambda t, c: None)

        result = await processor.process_batch()

        assert isinstance(result, BatchResult)
        assert len(result.results) == 0
        assert result.success_rate == 0.0

    @pytest.mark.asyncio()
    async def test_handles_failed_task(self, sample_task):
        """[P0] Should handle task failure gracefully."""

        def mock_executor(task, context):
            if task.id == "task-1":
                return ExecutionResult(
                    success=False,
                    output="Error",
                    error_type="ValueError",
                    error_message="Failed",
                )
            return ExecutionResult(success=True, output="done")

        processor = BatchProcessor(executor=mock_executor)
        processor.add_task(sample_task)

        result = await processor.process_batch()

        assert len(result.results) == 1
        assert result.results[0].success is False
        assert len(result.failed_tasks) == 1
        assert result.success_rate == 0.0

    @pytest.mark.asyncio()
    async def test_mixed_success_and_failure(self):
        """[P0] Should handle mixed success/failure."""
        task1 = Task(id="task-1", description="T1", skill_name="s", operation_type="g")
        task2 = Task(id="task-2", description="T2", skill_name="s", operation_type="g")
        task3 = Task(id="task-3", description="T3", skill_name="s", operation_type="g")

        def mock_executor(task, context):
            if task.id == "task-2":
                return ExecutionResult(success=False, output="fail")
            return ExecutionResult(success=True, output="done")

        processor = BatchProcessor(executor=mock_executor)
        processor.add_task(task1)
        processor.add_task(task2)
        processor.add_task(task3)

        result = await processor.process_batch()

        assert len(result.results) == 3
        assert len(result.failed_tasks) == 1
        assert result.success_rate == pytest.approx(0.67, 0.01)

    @pytest.mark.asyncio()
    async def test_concurrency_limit(self):
        """[P1] Should respect max batch size."""
        execution_count = 0

        def mock_executor(task, context):
            nonlocal execution_count
            execution_count += 1
            return ExecutionResult(
                success=True,
                output=f"done-{task.id}",
                metrics=ExecutionMetrics(tokens=100),
            )

        processor = BatchProcessor(
            executor=mock_executor,
            config=BatchConfig(max_batch_size=3, optimal_batch_size=2),
        )

        # Add 5 tasks
        for i in range(5):
            processor.add_task(
                Task(
                    id=f"task-{i}",
                    description="Test",
                    skill_name="s",
                    operation_type="g",
                )
            )

        result = await processor.process_batch()

        # Should process max_batch_size tasks (3), leaving 2 in queue
        assert len(result.results) == 3
        assert processor.get_queue_size() == 2


class TestBatchResult:
    """[P0] Tests for BatchResult."""

    def test_empty_result(self):
        """[P0] Should handle empty result."""
        result = BatchResult()

        assert result.results == []
        assert result.failed_tasks == []
        assert result.success_rate == 0.0

    def test_success_rate_calculation(self):
        """[P0] Should calculate success rate correctly."""
        result = BatchResult(
            results=[
                ExecutionResult(success=True, output="1"),
                ExecutionResult(success=True, output="2"),
                ExecutionResult(success=False, output="3"),
                ExecutionResult(success=True, output="4"),
            ],
            failed_tasks=[Task(id="t3", description="", skill_name="", operation_type="")],
        )

        assert result.success_rate == 0.75

    def test_all_success(self):
        """[P0] Should report 100% success rate."""
        result = BatchResult(
            results=[
                ExecutionResult(success=True, output="1"),
                ExecutionResult(success=True, output="2"),
            ],
            failed_tasks=[],
        )

        assert result.success_rate == 1.0

    def test_all_failure(self):
        """[P0] Should report 0% success rate."""
        result = BatchResult(
            results=[
                ExecutionResult(success=False, output="1"),
                ExecutionResult(success=False, output="2"),
            ],
            failed_tasks=[
                Task(id="t1", description="", skill_name="", operation_type=""),
                Task(id="t2", description="", skill_name="", operation_type=""),
            ],
        )

        assert result.success_rate == 0.0


class TestSimpleBatch:
    """[P1] Tests for SimpleBatch."""

    def test_process_sequential(self):
        """[P1] Should process tasks sequentially."""
        task1 = Task(id="t1", description="T1", skill_name="s", operation_type="g")
        task2 = Task(id="t2", description="T2", skill_name="s", operation_type="g")

        executed_order = []

        def executor(task, context):
            executed_order.append(task.id)
            return ExecutionResult(success=True, output=f"done-{task.id}")

        batch = SimpleBatch(executor=executor)
        results = batch.process([task1, task2])

        assert len(results) == 2
        assert executed_order == ["t1", "t2"]  # Sequential order

    def test_process_single_task(self):
        """[P1] Should handle single task."""
        task = Task(id="t1", description="T", skill_name="s", operation_type="g")

        batch = SimpleBatch(executor=lambda t, c: ExecutionResult(success=True, output="done"))
        results = batch.process([task])

        assert len(results) == 1
        assert results[0].success is True

    def test_process_empty_list(self):
        """[P1] Should handle empty task list."""
        batch = SimpleBatch(executor=lambda t, c: None)
        results = batch.process([])

        assert results == []
