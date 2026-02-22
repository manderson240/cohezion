"""Python client for the Trigger.dev REST management API.

Allows Cohezion to trigger, monitor, and manage background tasks
from Python without needing the TypeScript SDK.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from cohezion.triggers.config import TriggerConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class RunHandle:
    """Handle returned after triggering a task run."""

    id: str
    task_id: str
    status: str = "QUEUED"
    output: Any = None

    @classmethod
    def from_response(cls, task_id: str, data: dict[str, Any]) -> RunHandle:
        return cls(id=data.get("id", ""), task_id=task_id)


@dataclass
class RunStatus:
    """Status of a task run."""

    id: str
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    output: Any = None

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> RunStatus:
        return cls(
            id=data.get("id", ""),
            status=data.get("status", "UNKNOWN"),
            started_at=data.get("startedAt"),
            finished_at=data.get("finishedAt"),
            output=data.get("output"),
        )


@dataclass
class ScheduleHandle:
    """Handle for a managed schedule."""

    id: str
    task_id: str
    cron: str
    active: bool = True

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> ScheduleHandle:
        return cls(
            id=data.get("id", ""),
            task_id=data.get("taskIdentifier", ""),
            cron=data.get("cron", ""),
            active=data.get("active", True),
        )


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class TriggerClient:
    """Typed Python client for the Trigger.dev REST API.

    Usage
    -----
    >>> client = TriggerClient()
    >>> run = await client.trigger("health-check", {"scope": "full"})
    >>> status = await client.get_run(run.id)
    """

    def __init__(self, config: TriggerConfig | None = None) -> None:
        self.config = config or TriggerConfig()
        self._client: httpx.AsyncClient | None = None

    # -- lifecycle -----------------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.api_url,
                headers=self.config.headers,
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # -- tasks ---------------------------------------------------------------

    async def trigger(
        self,
        task_id: str,
        payload: dict[str, Any] | None = None,
        *,
        idempotency_key: str | None = None,
        queue: str | None = None,
        delay: str | None = None,
        tags: list[str] | None = None,
        priority: int | None = None,
    ) -> RunHandle:
        """Trigger a single task run.

        Parameters
        ----------
        task_id : str
            The registered task identifier (e.g. ``"research/model-scout"``).
        payload : dict, optional
            JSON-serializable payload for the task.
        idempotency_key : str, optional
            Prevents duplicate runs within a window.
        queue : str, optional
            Override default queue.
        delay : str, optional
            Delay before execution (e.g. ``"5m"``, ``"1h"``).
        tags : list[str], optional
            Up to 5 tags for filtering/querying runs.
        priority : int, optional
            Higher priority runs execute first.
        """
        client = await self._get_client()

        body: dict[str, Any] = {}
        if payload:
            body["payload"] = payload

        options: dict[str, Any] = {}
        if idempotency_key:
            options["idempotencyKey"] = idempotency_key
        if queue:
            options["queue"] = {"name": queue}
        if delay:
            options["delay"] = delay
        if tags:
            options["tags"] = tags[:5]
        if priority is not None:
            options["priority"] = priority
        if options:
            body["options"] = options

        resp = await client.post(f"/api/v1/tasks/{task_id}/trigger", json=body)
        resp.raise_for_status()
        data = resp.json()
        logger.info("Triggered task %s -> run %s", task_id, data.get("id"))
        return RunHandle.from_response(task_id, data)

    async def batch_trigger(
        self,
        task_id: str,
        payloads: list[dict[str, Any]],
        *,
        queue: str | None = None,
    ) -> list[RunHandle]:
        """Trigger multiple runs of the same task.

        Parameters
        ----------
        task_id : str
            The task identifier.
        payloads : list[dict]
            List of payloads (up to 1000).
        queue : str, optional
            Override default queue.
        """
        client = await self._get_client()

        items = []
        for p in payloads[:1000]:
            item: dict[str, Any] = {"payload": p}
            if queue:
                item["options"] = {"queue": {"name": queue}}
            items.append(item)

        resp = await client.post(
            f"/api/v1/tasks/{task_id}/batchTrigger",
            json={"items": items},
        )
        resp.raise_for_status()
        data = resp.json()
        runs = data.get("runs", [])
        logger.info("Batch triggered %d runs for %s", len(runs), task_id)
        return [RunHandle.from_response(task_id, r) for r in runs]

    # -- runs ----------------------------------------------------------------

    async def get_run(self, run_id: str) -> RunStatus:
        """Get the current status of a run."""
        client = await self._get_client()
        resp = await client.get(f"/api/v1/runs/{run_id}")
        resp.raise_for_status()
        return RunStatus.from_response(resp.json())

    async def list_runs(
        self,
        *,
        status: list[str] | None = None,
        task_id: str | None = None,
        limit: int = 20,
    ) -> list[RunStatus]:
        """List recent runs with optional filters."""
        client = await self._get_client()
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        if task_id:
            params["taskIdentifier"] = task_id
        resp = await client.get("/api/v1/runs", params=params)
        resp.raise_for_status()
        data = resp.json()
        return [RunStatus.from_response(r) for r in data.get("data", [])]

    async def cancel_run(self, run_id: str) -> bool:
        """Cancel a queued or in-progress run."""
        client = await self._get_client()
        resp = await client.post(f"/api/v1/runs/{run_id}/cancel")
        resp.raise_for_status()
        logger.info("Cancelled run %s", run_id)
        return True

    # -- schedules -----------------------------------------------------------

    async def create_schedule(
        self,
        task_id: str,
        cron: str,
        *,
        external_id: str | None = None,
        deduplication_key: str | None = None,
        timezone: str = "UTC",
    ) -> ScheduleHandle:
        """Create a recurring schedule for a task.

        Parameters
        ----------
        task_id : str
            Task identifier to schedule.
        cron : str
            Cron expression (5-field, e.g. ``"0 */6 * * *"`` for every 6h).
        external_id : str, optional
            External reference (e.g. user ID for multi-tenant).
        deduplication_key : str, optional
            Prevents duplicate schedule creation.
        timezone : str
            IANA timezone (default UTC).
        """
        client = await self._get_client()
        body: dict[str, Any] = {
            "task": task_id,
            "cron": cron,
            "timezone": timezone,
        }
        if external_id:
            body["externalId"] = external_id
        if deduplication_key:
            body["deduplicationKey"] = deduplication_key

        resp = await client.post("/api/v1/schedules", json=body)
        resp.raise_for_status()
        handle = ScheduleHandle.from_response(resp.json())
        logger.info("Created schedule %s for %s (%s)", handle.id, task_id, cron)
        return handle

    async def list_schedules(self) -> list[ScheduleHandle]:
        """List all schedules."""
        client = await self._get_client()
        resp = await client.get("/api/v1/schedules")
        resp.raise_for_status()
        data = resp.json()
        return [ScheduleHandle.from_response(s) for s in data.get("data", [])]

    async def deactivate_schedule(self, schedule_id: str) -> bool:
        """Temporarily disable a schedule."""
        client = await self._get_client()
        resp = await client.post(f"/api/v1/schedules/{schedule_id}/deactivate")
        resp.raise_for_status()
        return True

    async def activate_schedule(self, schedule_id: str) -> bool:
        """Re-enable a schedule."""
        client = await self._get_client()
        resp = await client.post(f"/api/v1/schedules/{schedule_id}/activate")
        resp.raise_for_status()
        return True

    async def delete_schedule(self, schedule_id: str) -> bool:
        """Permanently delete a schedule."""
        client = await self._get_client()
        resp = await client.delete(f"/api/v1/schedules/{schedule_id}")
        resp.raise_for_status()
        return True

    # -- queues --------------------------------------------------------------

    async def list_queues(self) -> list[dict[str, Any]]:
        """List all task queues."""
        client = await self._get_client()
        resp = await client.get("/api/v1/queues")
        resp.raise_for_status()
        return resp.json().get("data", [])

    async def pause_queue(self, queue_id: str) -> bool:
        """Pause a queue (no new runs will start)."""
        client = await self._get_client()
        resp = await client.post(f"/api/v1/queues/{queue_id}/pause")
        resp.raise_for_status()
        return True

    async def resume_queue(self, queue_id: str) -> bool:
        """Resume a paused queue."""
        client = await self._get_client()
        resp = await client.post(f"/api/v1/queues/{queue_id}/resume")
        resp.raise_for_status()
        return True
