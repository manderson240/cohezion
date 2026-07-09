# fire-and-forget async tasks — intentional
"""Task management for async operations with proper tracking and cleanup.

Prevents fire-and-forget issues and unhandled exceptions in background tasks.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import traceback
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine


logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status."""

    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass(slots=True)
class TaskInfo:
    """Metadata for tracked tasks."""

    task_id: str
    name: str
    coro_name: str
    created_at: datetime
    status: TaskStatus
    result: Any = None
    error: Exception | None = None
    traceback: str | None = None
    completed_at: datetime | None = None


class TaskManager:
    """Centralized async task management with tracking and cleanup.

    Usage:
        manager = TaskManager()

        # Fire and properly track
        task = await manager.create_task(
            my_coroutine(),
            name="background_job",
            on_complete=on_done_callback
        )

        # Cleanup on shutdown
        await manager.cleanup()
    """

    def __init__(self, max_concurrent: int = 100):
        self._tasks: dict[str, asyncio.Task] = {}
        self._info: dict[str, TaskInfo] = {}
        self._callbacks: dict[str, list[Callable[[TaskInfo], Awaitable[None]]]] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._lock = asyncio.Lock()
        self._counter = 0
        self._metrics = {
            "created": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
        }

    async def create_task(
        self,
        coro: Coroutine[Any, Any, Any],
        name: str | None = None,
        on_complete: Callable[[TaskInfo], Awaitable[None]] | None = None,
        on_error: Callable[[TaskInfo], Awaitable[None]] | None = None,
    ) -> str:
        """Create a tracked background task.

        Args:
            coro: Coroutine to execute
            name: Human-readable task name
            on_complete: Callback when task completes successfully
            on_error: Callback when task fails

        Returns:
            Task ID for tracking
        """
        async with self._lock:
            self._counter += 1
            task_id = f"task_{self._counter}_{asyncio.get_event_loop().time()}"

            info = TaskInfo(
                task_id=task_id,
                name=name or coro.__name__,
                coro_name=coro.__name__,
                created_at=datetime.now(),
                status=TaskStatus.PENDING,
            )
            self._info[task_id] = info
            self._metrics["created"] += 1

            # Store callbacks
            if on_complete or on_error:
                self._callbacks[task_id] = []
                if on_complete:
                    self._callbacks[task_id].append(on_complete)
                if on_error:
                    self._callbacks[task_id].append(on_error)

            # Create wrapped coroutine
            async def wrapped():
                async with self._semaphore:
                    info.status = TaskStatus.RUNNING
                    try:
                        result = await coro
                        info.status = TaskStatus.COMPLETED
                        info.result = result
                        info.completed_at = datetime.now()
                        self._metrics["completed"] += 1

                        # Call on_complete callbacks
                        for callback in self._callbacks.get(task_id, []):
                            try:
                                await callback(info)
                            except Exception as e:
                                logger.error(f"Task callback error: {e}")

                        return result

                    except asyncio.CancelledError:
                        info.status = TaskStatus.CANCELLED
                        self._metrics["cancelled"] += 1
                        raise

                    except Exception as e:
                        info.status = TaskStatus.FAILED
                        info.error = e
                        info.traceback = traceback.format_exc()
                        info.completed_at = datetime.now()
                        self._metrics["failed"] += 1

                        logger.error(f"Task {task_id} failed: {e}")

                        # Call on_error callbacks
                        for callback in self._callbacks.get(task_id, []):
                            try:
                                await callback(info)
                            except Exception as cb_e:
                                logger.error(f"Task error callback failed: {cb_e}")

                        raise

                    finally:
                        # Cleanup after a delay to allow status inspection
                        asyncio.create_task(self._delayed_cleanup(task_id))

            # Create and store task
            task = asyncio.create_task(wrapped(), name=task_id)
            self._tasks[task_id] = task

            return task_id

    async def _delayed_cleanup(self, task_id: str, delay: float = 60.0) -> None:
        """Remove task after delay to allow status inspection."""
        await asyncio.sleep(delay)
        async with self._lock:
            self._tasks.pop(task_id, None)
            self._info.pop(task_id, None)
            self._callbacks.pop(task_id, None)

    async def cancel_task(self, task_id: str, wait: bool = False) -> bool:
        """Cancel a running task.

        Args:
            task_id: Task to cancel
            wait: If True, wait for task to actually cancel

        Returns:
            True if task was found and cancelled
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False

            task.cancel()

            if wait and not task.done():
                with contextlib.suppress(asyncio.CancelledError):
                    await task

            return True

    async def get_task_info(self, task_id: str) -> TaskInfo | None:
        """Get information about a task."""
        async with self._lock:
            return self._info.get(task_id)

    async def list_tasks(
        self, status: TaskStatus | None = None, limit: int = 100
    ) -> list[TaskInfo]:
        """List tracked tasks with optional filtering."""
        async with self._lock:
            tasks = list(self._info.values())

            if status:
                tasks = [t for t in tasks if t.status == status]

            # Sort by creation time (newest first)
            tasks.sort(key=lambda t: t.created_at, reverse=True)
            return tasks[:limit]

    async def cleanup(self, cancel_running: bool = True) -> dict[str, int]:
        """Clean up all tasks.

        Args:
            cancel_running: If True, cancel running tasks

        Returns:
            Counts of cancelled, completed, failed tasks
        """
        async with self._lock:
            counts = {"cancelled": 0, "completed": 0, "failed": 0}

            for _, task in list(self._tasks.items()):
                if not task.done():
                    if cancel_running:
                        task.cancel()
                        counts["cancelled"] += 1
                    else:
                        continue
                else:
                    if task.cancelled():
                        counts["cancelled"] += 1
                    elif task.exception():
                        counts["failed"] += 1
                    else:
                        counts["completed"] += 1

            # Wait for cancellations
            if cancel_running:
                await asyncio.gather(*self._tasks.values(), return_exceptions=True)

            self._tasks.clear()
            self._info.clear()
            self._callbacks.clear()

            return counts

    def get_metrics(self) -> dict[str, Any]:
        """Get task manager metrics."""
        return {
            **self._metrics,
            "active_tasks": len([t for t in self._tasks.values() if not t.done()]),
            "total_tracked": len(self._tasks),
        }


class TaskGroup:
    """Group related tasks for coordinated management."""

    def __init__(self, manager: TaskManager, name: str):
        self._manager = manager
        self.name = name
        self._task_ids: list[str] = []

    async def create_task(self, coro: Coroutine[Any, Any, Any], **kwargs) -> str:
        """Create task in this group."""
        task_id = await self._manager.create_task(coro, **kwargs)
        self._task_ids.append(task_id)
        return task_id

    async def cancel_all(self, wait: bool = False) -> int:
        """Cancel all tasks in group."""
        cancelled = 0
        for task_id in self._task_ids:
            if await self._manager.cancel_task(task_id, wait):
                cancelled += 1
        self._task_ids.clear()
        return cancelled

    async def wait_all(self, timeout: float | None = None) -> list[TaskInfo]:
        """Wait for all tasks to complete."""

        async def wait_for_task(task_id: str):
            while True:
                info = await self._manager.get_task_info(task_id)
                if info is None or info.status in (
                    TaskStatus.COMPLETED,
                    TaskStatus.FAILED,
                    TaskStatus.CANCELLED,
                ):
                    return info
                await asyncio.sleep(0.1)

        results = await asyncio.gather(
            *[wait_for_task(tid) for tid in self._task_ids], return_exceptions=True
        )

        return [r for r in results if isinstance(r, TaskInfo)]


# Global singleton
_task_manager: TaskManager | None = None


async def get_task_manager(max_concurrent: int = 100) -> TaskManager:
    """Get or create global task manager."""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager(max_concurrent=max_concurrent)
    return _task_manager


def reset_task_manager() -> None:
    """Reset global task manager (for testing)."""
    global _task_manager
    _task_manager = None
