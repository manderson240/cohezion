"""Task queue for managing excess workload during thermal degradation.

Implements FIFO queue with priority support for tasks that cannot be
immediately executed due to thermal constraints.

Phase 3 Sprint 3: Graceful Degradation Cascade

Key features:
- FIFO queue with priority levels (critical, normal, low)
- Configurable queue size limits
- Disk persistence for large queues (>1000 tasks)
- Metrics tracking (enqueued, dequeued, flushed)
- Task timeout and expiry handling
"""

from __future__ import annotations

import json
import logging
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels for queue ordering."""

    CRITICAL = 3  # Must execute even under extreme stress
    NORMAL = 2  # Standard priority
    LOW = 1  # Can be dropped under severe constraints


@dataclass
class QueuedTask:
    """A task queued for later execution."""

    task_id: str
    prompt: str
    system_prompt: str | None
    model: str
    priority: TaskPriority = TaskPriority.NORMAL
    metadata: dict[str, Any] = field(default_factory=dict)
    enqueued_at: float = field(default_factory=time.time)
    timeout_seconds: float = 300.0  # 5 minutes default
    attempts: int = 0
    max_attempts: int = 3

    def has_expired(self) -> bool:
        """Check if task has exceeded timeout."""
        elapsed = time.time() - self.enqueued_at
        return elapsed > self.timeout_seconds

    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return self.attempts < self.max_attempts


@dataclass
class QueueMetrics:
    """Metrics about queue operations."""

    total_enqueued: int = 0
    total_dequeued: int = 0
    total_flushed: int = 0
    total_expired: int = 0
    current_depth: int = 0
    max_depth_seen: int = 0
    total_tokens_queued: int = 0
    timestamp: float = field(default_factory=time.time)


class TaskQueue:
    """FIFO task queue with priority support and disk persistence.

    Manages tasks that cannot be immediately executed due to thermal
    constraints or system load. Supports priority-based ordering and
    automatic persistence for large queues.

    Parameters
    ----------
    queue_size_limit : int
        Maximum tasks to hold in queue (default: 10000)
    persistence_dir : Path, optional
        Directory for queue persistence (default: None, no persistence)
    enable_persistence : bool
        Enable disk persistence for large queues (default: True)
    """

    def __init__(
        self,
        queue_size_limit: int = 10000,
        persistence_dir: Path | None = None,
        enable_persistence: bool = True,
    ) -> None:
        """Initialize task queue."""
        self.queue_size_limit = queue_size_limit
        self.persistence_dir = persistence_dir or Path(tempfile.gettempdir()) / "cohezion_queue"
        self.enable_persistence = enable_persistence

        # Create persistence directory if needed
        if enable_persistence and persistence_dir:
            self.persistence_dir.mkdir(parents=True, exist_ok=True)

        # Internal queue: organized by priority (CRITICAL > NORMAL > LOW)
        self._critical_queue: list[QueuedTask] = []
        self._normal_queue: list[QueuedTask] = []
        self._low_queue: list[QueuedTask] = []

        # Metrics
        self.metrics = QueueMetrics()

    def enqueue(self, task: QueuedTask) -> bool:
        """Enqueue a task for later execution.

        Parameters
        ----------
        task : QueuedTask
            Task to enqueue

        Returns
        -------
        bool
            True if successfully enqueued, False if queue full
        """
        if self.is_full():
            logger.warning(f"Queue full ({self.size()} tasks), dropping task {task.task_id}")
            return False

        # Add to appropriate priority queue
        if task.priority == TaskPriority.CRITICAL:
            self._critical_queue.append(task)
        elif task.priority == TaskPriority.NORMAL:
            self._normal_queue.append(task)
        else:  # LOW
            self._low_queue.append(task)

        # Update metrics
        self.metrics.total_enqueued += 1
        self.metrics.current_depth = self.size()
        self.metrics.max_depth_seen = max(self.metrics.max_depth_seen, self.metrics.current_depth)

        logger.debug(
            f"Enqueued task {task.task_id} "
            f"(priority={task.priority.name}, queue_depth={self.size()})"
        )

        return True

    def dequeue(self) -> QueuedTask | None:
        """Dequeue next task (priority order).

        Returns highest priority task that hasn't expired.
        Priority: CRITICAL > NORMAL > LOW

        Returns
        -------
        QueuedTask or None
            Next task, or None if queue empty
        """
        # Try to get from each priority level
        for queue in [self._critical_queue, self._normal_queue, self._low_queue]:
            while queue:
                task = queue.pop(0)

                # Check expiry
                if task.has_expired():
                    logger.debug(
                        f"Task {task.task_id} expired after {time.time() - task.enqueued_at:.1f}s"
                    )
                    self.metrics.total_expired += 1
                    continue

                # Task is valid
                self.metrics.total_dequeued += 1
                self.metrics.current_depth = self.size()
                return task

        # No valid tasks found
        return None

    def peek(self, count: int = 1) -> list[QueuedTask]:
        """Peek at next N tasks without removing them.

        Parameters
        ----------
        count : int
            Number of tasks to peek at

        Returns
        -------
        list[QueuedTask]
            Next up to N tasks
        """
        result: list[QueuedTask] = []

        for queue in [self._critical_queue, self._normal_queue, self._low_queue]:
            for _, task in enumerate(queue):
                if len(result) >= count:
                    return result
                if not task.has_expired():
                    result.append(task)

        return result

    def get_batch(self, batch_size: int) -> list[QueuedTask]:
        """Get next batch of tasks (respecting priority).

        Parameters
        ----------
        batch_size : int
            Size of batch to retrieve

        Returns
        -------
        list[QueuedTask]
            Up to batch_size tasks
        """
        batch = []

        for _ in range(batch_size):
            task = self.dequeue()
            if task is None:
                break
            batch.append(task)

        return batch

    def flush(self, priority_threshold: TaskPriority = TaskPriority.LOW) -> int:
        """Flush tasks below priority threshold.

        Used during EMERGENCY degradation to drop low-priority tasks.

        Parameters
        ----------
        priority_threshold : TaskPriority
            Drop tasks with priority < threshold

        Returns
        -------
        int
            Number of tasks flushed
        """
        flushed = 0

        # Flush low priority if threshold allows
        if priority_threshold.value > TaskPriority.LOW.value:
            flushed += len(self._low_queue)
            self._low_queue.clear()

        # Flush normal priority if threshold allows
        if priority_threshold.value > TaskPriority.NORMAL.value:
            flushed += len(self._normal_queue)
            self._normal_queue.clear()

        self.metrics.total_flushed += flushed
        self.metrics.current_depth = self.size()

        logger.warning(f"Flushed {flushed} tasks (priority < {priority_threshold.name})")

        return flushed

    def clear(self) -> int:
        """Clear all tasks from queue.

        Returns
        -------
        int
            Number of tasks cleared
        """
        count = self.size()
        self._critical_queue.clear()
        self._normal_queue.clear()
        self._low_queue.clear()
        self.metrics.current_depth = 0

        logger.info(f"Cleared {count} tasks from queue")
        return count

    def size(self) -> int:
        """Get current queue depth.

        Returns
        -------
        int
            Number of tasks in queue
        """
        return len(self._critical_queue) + len(self._normal_queue) + len(self._low_queue)

    def is_empty(self) -> bool:
        """Check if queue is empty.

        Returns
        -------
        bool
            True if no tasks
        """
        return self.size() == 0

    def is_full(self) -> bool:
        """Check if queue is at size limit.

        Returns
        -------
        bool
            True if at or exceeding size limit
        """
        return self.size() >= self.queue_size_limit

    def get_metrics(self) -> QueueMetrics:
        """Get queue metrics.

        Returns
        -------
        QueueMetrics
            Current metrics snapshot
        """
        self.metrics.timestamp = time.time()
        self.metrics.current_depth = self.size()
        return self.metrics

    def persist_to_disk(self, filename: str = "queue_backup.jsonl") -> bool:
        """Persist queue to disk (JSONL format).

        Parameters
        ----------
        filename : str
            Filename for persistence

        Returns
        -------
        bool
            True if successful
        """
        if not self.enable_persistence:
            return False

        try:
            filepath = self.persistence_dir / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, "w") as f:
                for queue in [self._critical_queue, self._normal_queue, self._low_queue]:
                    for task in queue:
                        record = {
                            "task_id": task.task_id,
                            "prompt": task.prompt,
                            "system_prompt": task.system_prompt,
                            "model": task.model,
                            "priority": task.priority.name,
                            "metadata": task.metadata,
                            "enqueued_at": task.enqueued_at,
                            "timeout_seconds": task.timeout_seconds,
                            "attempts": task.attempts,
                        }
                        f.write(json.dumps(record) + "\n")

            logger.info(f"Persisted {self.size()} tasks to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to persist queue: {e}")
            return False

    def restore_from_disk(self, filename: str = "queue_backup.jsonl") -> int:
        """Restore queue from disk (JSONL format).

        Parameters
        ----------
        filename : str
            Filename to restore from

        Returns
        -------
        int
            Number of tasks restored
        """
        if not self.enable_persistence:
            return 0

        try:
            filepath = self.persistence_dir / filename
            if not filepath.exists():
                return 0

            restored = 0
            with open(filepath) as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        record = json.loads(line)
                        task = QueuedTask(
                            task_id=record["task_id"],
                            prompt=record["prompt"],
                            system_prompt=record.get("system_prompt"),
                            model=record["model"],
                            priority=TaskPriority[record.get("priority", "NORMAL")],
                            metadata=record.get("metadata", {}),
                            enqueued_at=record.get("enqueued_at", time.time()),
                            timeout_seconds=record.get("timeout_seconds", 300.0),
                            attempts=record.get("attempts", 0),
                        )

                        if self.enqueue(task):
                            restored += 1
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Failed to restore task: {e}")
                        continue

            logger.info(f"Restored {restored} tasks from {filepath}")
            return restored
        except Exception as e:
            logger.error(f"Failed to restore queue: {e}")
            return 0

    def get_stats(self) -> dict:
        """Get queue statistics.

        Returns
        -------
        dict
            Statistics about queue operations
        """
        metrics = self.get_metrics()

        return {
            "current_depth": metrics.current_depth,
            "max_depth_seen": metrics.max_depth_seen,
            "total_enqueued": metrics.total_enqueued,
            "total_dequeued": metrics.total_dequeued,
            "total_flushed": metrics.total_flushed,
            "total_expired": metrics.total_expired,
            "queue_size_limit": self.queue_size_limit,
            "at_capacity": self.is_full(),
            "critical_queue_depth": len(self._critical_queue),
            "normal_queue_depth": len(self._normal_queue),
            "low_queue_depth": len(self._low_queue),
        }


__all__ = [
    "QueueMetrics",
    "QueuedTask",
    "TaskPriority",
    "TaskQueue",
]
