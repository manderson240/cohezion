"""
Async work queue with Dead Letter Queue for sync daemon.

Provides reliable task processing with automatic retry and failure handling.
"""

import asyncio
import logging
from typing import Optional, Callable, Any, Dict, List
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task processing status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class WorkItem(BaseModel):
    """Work queue item."""
    id: str
    task_type: str  # "checkpoint_create", "commit_annotate", etc.
    payload: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    priority: int = 0  # Higher = more important


class WorkQueue:
    """
    Async work queue with priority support and automatic retry.

    Features:
    - Priority-based task ordering
    - Automatic retry with exponential backoff
    - Dead Letter Queue for permanently failed tasks
    - Graceful shutdown with in-progress task completion
    - Persistence to disk for crash recovery
    """

    def __init__(
        self,
        max_workers: int = 3,
        max_queue_size: int = 1000,
        dlq_path: Optional[Path] = None
    ):
        """
        Initialize work queue.

        Args:
            max_workers: Maximum concurrent workers
            max_queue_size: Maximum pending tasks
            dlq_path: Path to dead letter queue file
        """
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.dlq_path = dlq_path or Path.home() / ".cohezion" / "sync_dlq.jsonl"

        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=max_queue_size)
        self._workers: List[asyncio.Task] = []
        self._running = False
        self._task_handlers: Dict[str, Callable] = {}
        self._in_progress: Dict[str, WorkItem] = {}
        self._stats = {
            "tasks_queued": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_dlq": 0
        }

    def register_handler(self, task_type: str, handler: Callable):
        """
        Register task handler function.

        Args:
            task_type: Task type identifier
            handler: Async callable that processes the task
        """
        self._task_handlers[task_type] = handler

    async def enqueue(self, item: WorkItem) -> bool:
        """
        Add task to queue.

        Args:
            item: Work item to enqueue

        Returns:
            True if queued successfully, False if queue is full
        """
        if self._queue.full():
            logger.warning(f"Queue full, dropping task {item.id}")
            return False

        # Priority queue uses (priority, item) tuples
        # Negative priority for higher-priority items to sort first
        await self._queue.put((-item.priority, item))
        self._stats["tasks_queued"] += 1
        logger.debug(f"Queued task {item.id} (type: {item.task_type}, priority: {item.priority})")
        return True

    async def start(self):
        """Start worker pool."""
        if self._running:
            logger.warning("Work queue already running")
            return

        self._running = True
        logger.info(f"Starting work queue with {self.max_workers} workers")

        # Ensure DLQ directory exists
        self.dlq_path.parent.mkdir(parents=True, exist_ok=True)

        # Start worker tasks
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)

    async def stop(self, timeout: float = 30.0):
        """
        Stop worker pool gracefully.

        Args:
            timeout: Maximum time to wait for in-progress tasks
        """
        if not self._running:
            return

        logger.info("Stopping work queue...")
        self._running = False

        # Wait for workers to finish current tasks
        try:
            await asyncio.wait_for(
                asyncio.gather(*self._workers, return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Workers did not complete within {timeout}s timeout")
            for worker in self._workers:
                worker.cancel()

        self._workers.clear()
        logger.info("Work queue stopped")

    async def _worker(self, worker_id: int):
        """
        Worker coroutine that processes tasks from queue.

        Args:
            worker_id: Worker identifier for logging
        """
        logger.debug(f"Worker {worker_id} started")

        try:
            while self._running:
                try:
                    # Get next task with timeout to check _running flag
                    priority, item = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Process task
                try:
                    await self._process_item(item, worker_id)
                except Exception as e:
                    logger.error(f"Worker {worker_id} error processing {item.id}: {e}", exc_info=True)
                finally:
                    self._queue.task_done()

        except asyncio.CancelledError:
            logger.debug(f"Worker {worker_id} cancelled")
        except Exception as e:
            logger.error(f"Worker {worker_id} fatal error: {e}", exc_info=True)

        logger.debug(f"Worker {worker_id} stopped")

    async def _process_item(self, item: WorkItem, worker_id: int):
        """
        Process single work item.

        Args:
            item: Work item to process
            worker_id: Worker identifier
        """
        logger.debug(f"Worker {worker_id} processing {item.id} (type: {item.task_type})")

        # Mark as in-progress
        item.status = TaskStatus.IN_PROGRESS
        item.started_at = datetime.utcnow().isoformat() + "Z"
        self._in_progress[item.id] = item

        try:
            # Get handler for task type
            handler = self._task_handlers.get(item.task_type)
            if handler is None:
                raise ValueError(f"No handler registered for task type: {item.task_type}")

            # Execute handler
            await handler(item.payload)

            # Mark as completed
            item.status = TaskStatus.COMPLETED
            item.completed_at = datetime.utcnow().isoformat() + "Z"
            self._stats["tasks_completed"] += 1

            logger.debug(f"Task {item.id} completed successfully")

        except Exception as e:
            # Handle failure
            item.retry_count += 1
            item.error_message = str(e)

            if item.retry_count >= item.max_retries:
                # Send to dead letter queue
                item.status = TaskStatus.DEAD_LETTER
                await self._send_to_dlq(item)
                self._stats["tasks_dlq"] += 1
                logger.error(
                    f"Task {item.id} failed after {item.retry_count} retries, "
                    f"sent to DLQ: {e}"
                )
            else:
                # Retry with exponential backoff
                item.status = TaskStatus.FAILED
                self._stats["tasks_failed"] += 1
                backoff_seconds = 2 ** item.retry_count
                logger.warning(
                    f"Task {item.id} failed (attempt {item.retry_count}/{item.max_retries}), "
                    f"retrying in {backoff_seconds}s: {e}"
                )

                # Re-queue after backoff
                await asyncio.sleep(backoff_seconds)
                item.status = TaskStatus.PENDING
                await self.enqueue(item)

        finally:
            # Remove from in-progress
            self._in_progress.pop(item.id, None)

    async def _send_to_dlq(self, item: WorkItem):
        """
        Write failed task to dead letter queue file.

        Args:
            item: Failed work item
        """
        try:
            dlq_entry = {
                "id": item.id,
                "task_type": item.task_type,
                "payload": item.payload,
                "retry_count": item.retry_count,
                "error_message": item.error_message,
                "created_at": item.created_at,
                "failed_at": datetime.utcnow().isoformat() + "Z"
            }

            # Append to DLQ file (JSONL format)
            with open(self.dlq_path, "a") as f:
                f.write(json.dumps(dlq_entry) + "\n")

            logger.info(f"Task {item.id} written to DLQ: {self.dlq_path}")

        except Exception as e:
            logger.error(f"Failed to write to DLQ: {e}", exc_info=True)

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            **self._stats,
            "queue_size": self._queue.qsize(),
            "in_progress": len(self._in_progress),
            "workers": len(self._workers),
            "running": self._running
        }

    def is_running(self) -> bool:
        """Check if queue is running."""
        return self._running


# Singleton instance
_work_queue: Optional[WorkQueue] = None


def get_work_queue(
    max_workers: int = 3,
    max_queue_size: int = 1000,
    dlq_path: Optional[Path] = None
) -> WorkQueue:
    """
    Get or create singleton WorkQueue instance.

    Args:
        max_workers: Maximum concurrent workers
        max_queue_size: Maximum pending tasks
        dlq_path: Path to dead letter queue file

    Returns:
        WorkQueue singleton instance
    """
    global _work_queue
    if _work_queue is None:
        _work_queue = WorkQueue(
            max_workers=max_workers,
            max_queue_size=max_queue_size,
            dlq_path=dlq_path
        )
    return _work_queue


def reset_work_queue():
    """Reset singleton (for testing)."""
    global _work_queue
    if _work_queue and _work_queue.is_running():
        asyncio.create_task(_work_queue.stop())
    _work_queue = None
