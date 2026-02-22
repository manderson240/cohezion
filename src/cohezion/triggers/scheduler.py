"""Schedule manager for Trigger.dev background tasks.

Handles initial setup, sync, and lifecycle management of all
Cohezion background task schedules.
"""

from __future__ import annotations

import logging
from typing import Any

from cohezion.triggers.client import TriggerClient, ScheduleHandle
from cohezion.triggers.tasks import (
    TaskDefinition,
    get_scheduled_tasks,
    get_task_registry,
)

logger = logging.getLogger(__name__)


class ScheduleManager:
    """Manages Trigger.dev schedules for all Cohezion background tasks.

    Provides idempotent sync: schedules are created with deduplication
    keys so calling ``sync_all`` multiple times is safe.
    """

    def __init__(self, client: TriggerClient | None = None) -> None:
        self.client = client or TriggerClient()
        self._synced: dict[str, ScheduleHandle] = {}

    async def sync_all(self) -> dict[str, ScheduleHandle]:
        """Create or update all scheduled tasks.

        Returns a map of task_id -> ScheduleHandle for all schedules.
        """
        tasks = get_scheduled_tasks()
        logger.info("Syncing %d scheduled tasks with Trigger.dev", len(tasks))

        results: dict[str, ScheduleHandle] = {}
        for task_def in tasks:
            try:
                handle = await self._sync_task(task_def)
                results[task_def.task_id] = handle
                logger.info(
                    "Synced schedule for %s (%s) -> %s",
                    task_def.task_id,
                    task_def.cron,
                    handle.id,
                )
            except Exception as e:
                logger.error("Failed to sync schedule for %s: %s", task_def.task_id, e)

        self._synced = results
        return results

    async def _sync_task(self, task_def: TaskDefinition) -> ScheduleHandle:
        """Create or update a single schedule (idempotent via dedup key)."""
        assert task_def.cron is not None
        return await self.client.create_schedule(
            task_id=task_def.task_id,
            cron=task_def.cron,
            deduplication_key=f"cohezion-{task_def.task_id}",
            timezone="UTC",
        )

    async def deactivate_all(self) -> int:
        """Deactivate all managed schedules. Returns count deactivated."""
        schedules = await self.client.list_schedules()
        count = 0
        for schedule in schedules:
            if schedule.active:
                await self.client.deactivate_schedule(schedule.id)
                count += 1
        logger.info("Deactivated %d schedules", count)
        return count

    async def activate_all(self) -> int:
        """Activate all managed schedules. Returns count activated."""
        schedules = await self.client.list_schedules()
        count = 0
        for schedule in schedules:
            if not schedule.active:
                await self.client.activate_schedule(schedule.id)
                count += 1
        logger.info("Activated %d schedules", count)
        return count

    async def get_status(self) -> dict[str, Any]:
        """Get current status of all schedules."""
        schedules = await self.client.list_schedules()
        registry = get_task_registry()

        active = [s for s in schedules if s.active]
        inactive = [s for s in schedules if not s.active]

        return {
            "total_schedules": len(schedules),
            "active": len(active),
            "inactive": len(inactive),
            "registered_tasks": len(registry),
            "scheduled_tasks": len(get_scheduled_tasks()),
            "schedules": [
                {
                    "id": s.id,
                    "task_id": s.task_id,
                    "cron": s.cron,
                    "active": s.active,
                    "description": registry[s.task_id].description
                    if s.task_id in registry
                    else "Unknown task",
                }
                for s in schedules
            ],
        }

    async def trigger_now(self, task_id: str, payload: dict[str, Any] | None = None) -> str:
        """Manually trigger a task outside its schedule.

        Returns the run ID.
        """
        handle = await self.client.trigger(
            task_id,
            payload,
            tags=["manual", "on-demand"],
        )
        logger.info("Manually triggered %s -> run %s", task_id, handle.id)
        return handle.id

    async def close(self) -> None:
        await self.client.close()
