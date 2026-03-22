"""Tests for TaskQueue - FIFO queue with priority support for degradation."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

import pytest

from cohezion.compound.task_queue import (
    QueuedTask,
    TaskPriority,
    TaskQueue,
)


@pytest.fixture
def queue():
    """Create a task queue instance."""
    return TaskQueue(queue_size_limit=1000, enable_persistence=False)


@pytest.fixture
def temp_queue_dir():
    """Create temporary directory for queue persistence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_task():
    """Create a sample task."""
    return QueuedTask(
        task_id="task_001",
        prompt="Write a hello world program",
        system_prompt="You are a helpful coding assistant",
        model="claude-3-5-sonnet",
        priority=TaskPriority.NORMAL,
    )


class TestTaskPriority:
    """Test TaskPriority enum."""

    def test_priority_values(self):
        """Test priority enum values."""
        assert TaskPriority.CRITICAL.value == 3
        assert TaskPriority.NORMAL.value == 2
        assert TaskPriority.LOW.value == 1

    def test_priority_ordering(self):
        """Test priority ordering."""
        assert TaskPriority.CRITICAL.value > TaskPriority.NORMAL.value
        assert TaskPriority.NORMAL.value > TaskPriority.LOW.value


class TestQueuedTask:
    """Test QueuedTask dataclass."""

    def test_initialization(self, sample_task):
        """Test task initialization."""
        assert sample_task.task_id == "task_001"
        assert sample_task.priority == TaskPriority.NORMAL
        assert sample_task.attempts == 0

    def test_has_not_expired(self, sample_task):
        """Test task hasn't expired immediately."""
        assert not sample_task.has_expired()

    def test_has_expired(self):
        """Test task expiry detection."""
        task = QueuedTask(
            task_id="task_001",
            prompt="test",
            system_prompt=None,
            model="claude",
            enqueued_at=time.time() - 400,  # 400 seconds ago
            timeout_seconds=300.0,  # 5 minute timeout
        )
        assert task.has_expired()

    def test_can_retry(self, sample_task):
        """Test retry capability."""
        sample_task.attempts = 0
        sample_task.max_attempts = 3
        assert sample_task.can_retry()

        sample_task.attempts = 3
        assert not sample_task.can_retry()


class TestTaskQueueInit:
    """Test queue initialization."""

    def test_initialization_defaults(self, queue):
        """Test initialization with defaults."""
        assert queue.queue_size_limit == 1000
        assert queue.is_empty()
        assert queue.size() == 0

    def test_initialization_custom_size(self):
        """Test initialization with custom size limit."""
        q = TaskQueue(queue_size_limit=100, enable_persistence=False)
        assert q.queue_size_limit == 100

    def test_initialization_with_persistence(self, temp_queue_dir):
        """Test initialization with persistence enabled."""
        q = TaskQueue(
            queue_size_limit=100,
            persistence_dir=temp_queue_dir,
            enable_persistence=True,
        )
        assert q.enable_persistence


class TestEnqueueDequeue:
    """Test basic enqueue/dequeue operations."""

    def test_enqueue_single_task(self, queue, sample_task):
        """Test enqueueing a single task."""
        result = queue.enqueue(sample_task)

        assert result is True
        assert queue.size() == 1

    def test_enqueue_multiple_tasks(self, queue):
        """Test enqueueing multiple tasks."""
        for i in range(5):
            task = QueuedTask(
                task_id=f"task_{i:03d}",
                prompt="test",
                system_prompt=None,
                model="claude",
            )
            queue.enqueue(task)

        assert queue.size() == 5

    def test_dequeue_fifo(self, queue):
        """Test FIFO ordering (normal priority)."""
        for i in range(3):
            task = QueuedTask(
                task_id=f"task_{i:03d}",
                prompt="test",
                system_prompt=None,
                model="claude",
                priority=TaskPriority.NORMAL,
            )
            queue.enqueue(task)

        # Dequeue should return in FIFO order
        t1 = queue.dequeue()
        t2 = queue.dequeue()
        t3 = queue.dequeue()

        assert t1.task_id == "task_000"
        assert t2.task_id == "task_001"
        assert t3.task_id == "task_002"

    def test_dequeue_empty_queue(self, queue):
        """Test dequeuing from empty queue."""
        result = queue.dequeue()
        assert result is None

    def test_enqueue_when_full(self, queue):
        """Test enqueueing when queue is full."""
        queue.queue_size_limit = 2

        task1 = QueuedTask(
            task_id="task_001",
            prompt="test",
            system_prompt=None,
            model="claude",
        )
        task2 = QueuedTask(
            task_id="task_002",
            prompt="test",
            system_prompt=None,
            model="claude",
        )
        task3 = QueuedTask(
            task_id="task_003",
            prompt="test",
            system_prompt=None,
            model="claude",
        )

        assert queue.enqueue(task1) is True
        assert queue.enqueue(task2) is True
        assert queue.enqueue(task3) is False  # Queue full
        assert queue.size() == 2


class TestPriorityOrdering:
    """Test priority-based task ordering."""

    def test_critical_before_normal(self, queue):
        """Test CRITICAL priority goes before NORMAL."""
        normal_task = QueuedTask(
            task_id="normal",
            prompt="test",
            system_prompt=None,
            model="claude",
            priority=TaskPriority.NORMAL,
        )
        critical_task = QueuedTask(
            task_id="critical",
            prompt="test",
            system_prompt=None,
            model="claude",
            priority=TaskPriority.CRITICAL,
        )

        # Enqueue normal first, then critical
        queue.enqueue(normal_task)
        queue.enqueue(critical_task)

        # Should dequeue critical first
        t1 = queue.dequeue()
        assert t1.task_id == "critical"

        t2 = queue.dequeue()
        assert t2.task_id == "normal"

    def test_normal_before_low(self, queue):
        """Test NORMAL priority goes before LOW."""
        low_task = QueuedTask(
            task_id="low",
            prompt="test",
            system_prompt=None,
            model="claude",
            priority=TaskPriority.LOW,
        )
        normal_task = QueuedTask(
            task_id="normal",
            prompt="test",
            system_prompt=None,
            model="claude",
            priority=TaskPriority.NORMAL,
        )

        queue.enqueue(low_task)
        queue.enqueue(normal_task)

        t1 = queue.dequeue()
        assert t1.task_id == "normal"

        t2 = queue.dequeue()
        assert t2.task_id == "low"

    def test_priority_preserves_fifo_within_level(self, queue):
        """Test FIFO within same priority level."""
        task1 = QueuedTask(
            task_id="normal_1",
            prompt="test",
            system_prompt=None,
            model="claude",
            priority=TaskPriority.NORMAL,
        )
        task2 = QueuedTask(
            task_id="normal_2",
            prompt="test",
            system_prompt=None,
            model="claude",
            priority=TaskPriority.NORMAL,
        )

        queue.enqueue(task1)
        queue.enqueue(task2)

        t1 = queue.dequeue()
        t2 = queue.dequeue()

        assert t1.task_id == "normal_1"
        assert t2.task_id == "normal_2"


class TestExpiry:
    """Test task expiry handling."""

    def test_expired_task_skipped(self, queue):
        """Test expired tasks are skipped during dequeue."""
        expired_task = QueuedTask(
            task_id="expired",
            prompt="test",
            system_prompt=None,
            model="claude",
            enqueued_at=time.time() - 400,
            timeout_seconds=300.0,
        )
        fresh_task = QueuedTask(
            task_id="fresh",
            prompt="test",
            system_prompt=None,
            model="claude",
        )

        queue.enqueue(expired_task)
        queue.enqueue(fresh_task)

        # Dequeue should skip expired and return fresh
        result = queue.dequeue()
        assert result.task_id == "fresh"

        # Check metrics
        assert queue.metrics.total_expired == 1

    def test_all_expired_returns_none(self, queue):
        """Test dequeue returns None when all tasks expired."""
        expired_task = QueuedTask(
            task_id="expired",
            prompt="test",
            system_prompt=None,
            model="claude",
            enqueued_at=time.time() - 400,
            timeout_seconds=300.0,
        )
        queue.enqueue(expired_task)

        result = queue.dequeue()
        assert result is None


class TestPeek:
    """Test peeking at queue without removing."""

    def test_peek_single(self, queue):
        """Test peeking at single task."""
        task = QueuedTask(
            task_id="task_001",
            prompt="test",
            system_prompt=None,
            model="claude",
        )
        queue.enqueue(task)

        peeked = queue.peek(1)
        assert len(peeked) == 1
        assert peeked[0].task_id == "task_001"

        # Queue should still have the task
        assert queue.size() == 1

    def test_peek_multiple(self, queue):
        """Test peeking at multiple tasks."""
        for i in range(3):
            task = QueuedTask(
                task_id=f"task_{i}",
                prompt="test",
                system_prompt=None,
                model="claude",
            )
            queue.enqueue(task)

        peeked = queue.peek(2)
        assert len(peeked) == 2
        assert queue.size() == 3  # Nothing removed


class TestGetBatch:
    """Test batch operations."""

    def test_get_batch(self, queue):
        """Test getting a batch of tasks."""
        for i in range(5):
            task = QueuedTask(
                task_id=f"task_{i}",
                prompt="test",
                system_prompt=None,
                model="claude",
            )
            queue.enqueue(task)

        batch = queue.get_batch(3)
        assert len(batch) == 3
        assert queue.size() == 2  # Remaining tasks

    def test_get_batch_smaller_than_requested(self, queue):
        """Test batch when queue has fewer tasks than requested."""
        task = QueuedTask(
            task_id="task_001",
            prompt="test",
            system_prompt=None,
            model="claude",
        )
        queue.enqueue(task)

        batch = queue.get_batch(5)
        assert len(batch) == 1


class TestFlush:
    """Test queue flushing."""

    def test_flush_low_priority(self, queue):
        """Test flushing low priority tasks."""
        queue.enqueue(
            QueuedTask(
                task_id="critical",
                prompt="test",
                system_prompt=None,
                model="claude",
                priority=TaskPriority.CRITICAL,
            )
        )
        queue.enqueue(
            QueuedTask(
                task_id="normal",
                prompt="test",
                system_prompt=None,
                model="claude",
                priority=TaskPriority.NORMAL,
            )
        )
        queue.enqueue(
            QueuedTask(
                task_id="low",
                prompt="test",
                system_prompt=None,
                model="claude",
                priority=TaskPriority.LOW,
            )
        )

        # Flush only LOW priority
        flushed = queue.flush(TaskPriority.NORMAL)
        assert flushed == 1
        assert queue.size() == 2

    def test_flush_all(self, queue):
        """Test flushing all tasks."""
        for i in range(3):
            queue.enqueue(
                QueuedTask(
                    task_id=f"task_{i}",
                    prompt="test",
                    system_prompt=None,
                    model="claude",
                )
            )

        queue.clear()
        assert queue.size() == 0


class TestMetrics:
    """Test queue metrics tracking."""

    def test_metrics_enqueued(self, queue, sample_task):
        """Test enqueued metrics."""
        queue.enqueue(sample_task)
        metrics = queue.get_metrics()

        assert metrics.total_enqueued == 1
        assert metrics.current_depth == 1

    def test_metrics_dequeued(self, queue, sample_task):
        """Test dequeued metrics."""
        queue.enqueue(sample_task)
        queue.dequeue()
        metrics = queue.get_metrics()

        assert metrics.total_dequeued == 1
        assert metrics.current_depth == 0

    def test_metrics_max_depth(self, queue):
        """Test max depth tracking."""
        for i in range(5):
            queue.enqueue(
                QueuedTask(
                    task_id=f"task_{i}",
                    prompt="test",
                    system_prompt=None,
                    model="claude",
                )
            )

        metrics = queue.get_metrics()
        assert metrics.max_depth_seen == 5


class TestPersistence:
    """Test disk persistence."""

    def test_persist_to_disk(self, temp_queue_dir):
        """Test persisting queue to disk."""
        queue = TaskQueue(
            queue_size_limit=100,
            persistence_dir=temp_queue_dir,
            enable_persistence=True,
        )

        for i in range(3):
            queue.enqueue(
                QueuedTask(
                    task_id=f"task_{i}",
                    prompt="test",
                    system_prompt=None,
                    model="claude",
                )
            )

        persisted = queue.persist_to_disk()
        assert persisted is True

        # Verify file exists
        filepath = temp_queue_dir / "queue_backup.jsonl"
        assert filepath.exists()

    def test_restore_from_disk(self, temp_queue_dir):
        """Test restoring queue from disk."""
        # Create and persist a queue
        queue1 = TaskQueue(
            queue_size_limit=100,
            persistence_dir=temp_queue_dir,
            enable_persistence=True,
        )

        for i in range(3):
            queue1.enqueue(
                QueuedTask(
                    task_id=f"task_{i}",
                    prompt="test",
                    system_prompt=None,
                    model="claude",
                )
            )

        queue1.persist_to_disk()

        # Create new queue and restore
        queue2 = TaskQueue(
            queue_size_limit=100,
            persistence_dir=temp_queue_dir,
            enable_persistence=True,
        )

        restored = queue2.restore_from_disk()
        assert restored == 3
        assert queue2.size() == 3


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_queue_stats(self, queue):
        """Test stats on empty queue."""
        stats = queue.get_stats()

        assert stats["current_depth"] == 0
        assert stats["total_enqueued"] == 0
        assert stats["total_dequeued"] == 0

    def test_queue_size_limit_edge(self):
        """Test queue at exactly size limit."""
        queue = TaskQueue(queue_size_limit=2, enable_persistence=False)

        t1 = QueuedTask(
            task_id="t1",
            prompt="test",
            system_prompt=None,
            model="claude",
        )
        t2 = QueuedTask(
            task_id="t2",
            prompt="test",
            system_prompt=None,
            model="claude",
        )

        assert queue.enqueue(t1) is True
        assert queue.enqueue(t2) is True
        assert queue.is_full()
        assert queue.size() == 2

    def test_mixed_priority_with_expiry(self, queue):
        """Test priority ordering with expired tasks."""
        expired_low = QueuedTask(
            task_id="expired_low",
            prompt="test",
            system_prompt=None,
            model="claude",
            priority=TaskPriority.LOW,
            enqueued_at=time.time() - 400,
            timeout_seconds=300.0,
        )
        fresh_normal = QueuedTask(
            task_id="fresh_normal",
            prompt="test",
            system_prompt=None,
            model="claude",
            priority=TaskPriority.NORMAL,
        )

        queue.enqueue(expired_low)
        queue.enqueue(fresh_normal)

        # Should skip expired_low and return fresh_normal
        result = queue.dequeue()
        assert result.task_id == "fresh_normal"
