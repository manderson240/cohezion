"""
Firestore Sync - Synchronization layer between local and cloud.

Provides bidirectional sync between the local swarm and Cloud Run:
- Polls for new tasks from Firestore
- Updates task status as processing completes
- Syncs results back to the cloud

This allows the "Universe" to persist even when the local simulation
is paused - tasks queue up in the cloud and process when resumed.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from cohezion.cloud.router import SwarmRouter, Task, TaskStatus

logger = logging.getLogger(__name__)


class FirestoreSync:
    """
    Synchronization layer between local swarm and Cloud Firestore.

    The local swarm polls this sync layer for new tasks, processes them,
    and reports results back. The cloud maintains the persistent queue.
    """

    def __init__(
        self,
        router: SwarmRouter | None = None,
        poll_interval_seconds: float = 5.0,
        batch_size: int = 5,
    ):
        """
        Initialize the Firestore sync layer.

        Args:
            router: SwarmRouter instance (creates new if not provided)
            poll_interval_seconds: How often to poll for new tasks
            batch_size: Maximum tasks to fetch per poll
        """
        self.router = router or SwarmRouter()
        self.poll_interval = poll_interval_seconds
        self.batch_size = batch_size

        self._running = False
        self._task_handler: Callable[[Task], Awaitable[dict[str, Any]]] | None = None
        self._poll_task: asyncio.Task | None = None

    async def initialize(self) -> bool:
        """Initialize the connection."""
        return await self.router.initialize()

    def set_task_handler(
        self,
        handler: Callable[[Task], Awaitable[dict[str, Any]]],
    ) -> None:
        """
        Set the function that processes tasks.

        Args:
            handler: Async function that takes a Task and returns results
        """
        self._task_handler = handler

    async def poll_for_tasks(self) -> list[Task]:
        """
        Poll Firestore for pending tasks.

        Returns tasks in priority order.
        """
        return await self.router.get_pending_tasks(limit=self.batch_size)

    async def claim_task(self, task: Task) -> bool:
        """
        Claim a task for processing.

        Atomically updates status to PROCESSING to prevent
        other workers from picking it up.

        Returns True if successfully claimed.
        """
        updated = await self.router.update_task_status(
            task.id,
            TaskStatus.PROCESSING,
        )
        return updated is not None

    async def complete_task(
        self,
        task: Task,
        result: dict[str, Any],
    ) -> None:
        """Mark a task as completed with results."""
        await self.router.update_task_status(
            task.id,
            TaskStatus.COMPLETED,
            result=result,
        )
        logger.info(f"Task {task.id} completed")

    async def fail_task(
        self,
        task: Task,
        error: str,
    ) -> None:
        """Mark a task as failed with error."""
        # Check if we should retry
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            await self.router.update_task_status(
                task.id,
                TaskStatus.PENDING,  # Reset to pending for retry
                error=f"Retry {task.retry_count}/{task.max_retries}: {error}",
            )
            logger.warning(
                f"Task {task.id} failed, will retry ({task.retry_count}/{task.max_retries})"
            )
        else:
            await self.router.update_task_status(
                task.id,
                TaskStatus.FAILED,
                error=error,
            )
            logger.error(f"Task {task.id} failed permanently: {error}")

    async def process_task(self, task: Task) -> None:
        """
        Process a single task using the registered handler.
        """
        if not self._task_handler:
            logger.error("No task handler registered")
            await self.fail_task(task, "No task handler registered")
            return

        try:
            # Claim the task
            if not await self.claim_task(task):
                logger.warning(
                    f"Failed to claim task {task.id}, may have been claimed by another worker"
                )
                return

            # Process it
            logger.info(f"Processing task {task.id}...")
            result = await self._task_handler(task)

            # Complete it
            await self.complete_task(task, result)

        except Exception as e:
            logger.error(f"Task processing failed: {e}")
            await self.fail_task(task, str(e))

    async def _poll_loop(self) -> None:
        """Background polling loop."""
        while self._running:
            try:
                tasks = await self.poll_for_tasks()

                if tasks:
                    logger.info(f"Found {len(tasks)} pending tasks")

                    # Process tasks concurrently
                    await asyncio.gather(
                        *[self.process_task(task) for task in tasks],
                        return_exceptions=True,
                    )

                await asyncio.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"Poll loop error: {e}")
                await asyncio.sleep(self.poll_interval)

    async def start(self) -> None:
        """Start the background polling."""
        if self._running:
            return

        self._running = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info("Firestore sync started")

    async def stop(self) -> None:
        """Stop the background polling."""
        self._running = False

        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass

        logger.info("Firestore sync stopped")

    async def run_once(self) -> int:
        """
        Run a single poll cycle.

        Useful for testing or cron-based triggering.

        Returns number of tasks processed.
        """
        tasks = await self.poll_for_tasks()

        if not tasks:
            return 0

        results = await asyncio.gather(
            *[self.process_task(task) for task in tasks],
            return_exceptions=True,
        )

        return sum(1 for r in results if not isinstance(r, Exception))

    async def __aenter__(self) -> "FirestoreSync":
        """Async context manager entry."""
        await self.initialize()
        await self.start()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.stop()


async def main() -> None:
    """Example usage of FirestoreSync."""
    import argparse

    parser = argparse.ArgumentParser(description="Firestore Sync Service")
    parser.add_argument("--once", action="store_true", help="Run single poll cycle")
    parser.add_argument("--interval", type=float, default=5.0, help="Poll interval")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    sync = FirestoreSync(poll_interval_seconds=args.interval)

    # Example task handler
    async def example_handler(task: Task) -> dict[str, Any]:
        """Process a task and return results."""
        logger.info(f"Handling task: {task.payload}")

        # Simulate processing
        await asyncio.sleep(1)

        return {
            "processed_at": datetime.now().isoformat(),
            "input": task.payload,
            "status": "success",
        }

    sync.set_task_handler(example_handler)

    if args.once:
        await sync.initialize()
        count = await sync.run_once()
        print(f"Processed {count} tasks")
    else:
        async with sync:
            print("Firestore sync running. Press Ctrl+C to stop.")
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    asyncio.run(main())
