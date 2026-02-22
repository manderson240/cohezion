"""FastAPI routes for Trigger.dev task management.

Provides REST endpoints for triggering, monitoring, and managing
background tasks from the Cohezion API.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cohezion.triggers.client import TriggerClient
from cohezion.triggers.config import TriggerConfig
from cohezion.triggers.scheduler import ScheduleManager
from cohezion.triggers.tasks import (
    TaskCategory,
    get_scheduled_tasks,
    get_task_registry,
    get_tasks_by_category,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/triggers", tags=["triggers"])

# Singleton instances (lazy init)
_client: TriggerClient | None = None
_scheduler: ScheduleManager | None = None


def _get_client() -> TriggerClient:
    global _client
    if _client is None:
        _client = TriggerClient()
    return _client


def _get_scheduler() -> ScheduleManager:
    global _scheduler
    if _scheduler is None:
        _scheduler = ScheduleManager(_get_client())
    return _scheduler


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------


class TriggerRequest(BaseModel):
    """Request to trigger a task."""

    task_id: str = Field(..., description="Task identifier (e.g. 'health/test-suite')")
    payload: dict[str, Any] | None = Field(default=None, description="Task payload")
    idempotency_key: str | None = Field(default=None, description="Prevent duplicate runs")
    delay: str | None = Field(default=None, description="Delay before execution (e.g. '5m')")
    tags: list[str] | None = Field(default=None, description="Run tags (max 5)")


class TriggerResponse(BaseModel):
    """Response after triggering a task."""

    run_id: str
    task_id: str
    status: str = "QUEUED"


class TaskInfo(BaseModel):
    """Task definition info."""

    task_id: str
    category: str
    description: str
    cron: str | None
    priority: int
    max_concurrent: int
    timeout_seconds: int
    tags: list[str]


class ScheduleStatusResponse(BaseModel):
    """Schedule status overview."""

    total_schedules: int
    active: int
    inactive: int
    registered_tasks: int
    scheduled_tasks: int
    schedules: list[dict[str, Any]]


class RunStatusResponse(BaseModel):
    """Run status."""

    id: str
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    output: Any = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/tasks")
async def list_tasks(category: str | None = None) -> dict[str, Any]:
    """List all registered task definitions.

    Optionally filter by category: research, simulation, health, compound.
    """
    if category:
        try:
            cat = TaskCategory(category)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category: {category}. Valid: {[c.value for c in TaskCategory]}",
            )
        tasks = get_tasks_by_category(cat)
    else:
        tasks = list(get_task_registry().values())

    return {
        "tasks": [
            TaskInfo(
                task_id=t.task_id,
                category=t.category.value,
                description=t.description,
                cron=t.cron,
                priority=t.priority.value,
                max_concurrent=t.max_concurrent,
                timeout_seconds=t.timeout_seconds,
                tags=t.tags,
            ).model_dump()
            for t in tasks
        ],
        "total": len(tasks),
    }


@router.post("/trigger", response_model=TriggerResponse)
async def trigger_task(request: TriggerRequest) -> TriggerResponse:
    """Trigger a background task on-demand.

    The task will be queued and executed by Trigger.dev workers.
    """
    registry = get_task_registry()
    if request.task_id not in registry:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown task: {request.task_id}. Available: {list(registry)}",
        )

    config = TriggerConfig()
    if not config.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Trigger.dev not configured. Set TRIGGER_SECRET_KEY.",
        )

    client = _get_client()
    try:
        handle = await client.trigger(
            request.task_id,
            request.payload,
            idempotency_key=request.idempotency_key,
            delay=request.delay,
            tags=request.tags,
        )
        return TriggerResponse(
            run_id=handle.id,
            task_id=handle.task_id,
            status=handle.status,
        )
    except Exception as e:
        logger.error("Failed to trigger task %s: %s", request.task_id, e)
        raise HTTPException(status_code=502, detail=f"Trigger.dev error: {e}")


@router.get("/runs/{run_id}", response_model=RunStatusResponse)
async def get_run_status(run_id: str) -> RunStatusResponse:
    """Get the status of a task run."""
    config = TriggerConfig()
    if not config.is_configured:
        raise HTTPException(status_code=503, detail="Trigger.dev not configured.")

    client = _get_client()
    try:
        status = await client.get_run(run_id)
        return RunStatusResponse(
            id=status.id,
            status=status.status,
            started_at=status.started_at,
            finished_at=status.finished_at,
            output=status.output,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Trigger.dev error: {e}")


@router.get("/runs")
async def list_runs(
    status: str | None = None,
    task_id: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """List recent task runs with optional filters."""
    config = TriggerConfig()
    if not config.is_configured:
        raise HTTPException(status_code=503, detail="Trigger.dev not configured.")

    client = _get_client()
    try:
        statuses = [status] if status else None
        runs = await client.list_runs(status=statuses, task_id=task_id, limit=limit)
        return {
            "runs": [
                RunStatusResponse(
                    id=r.id,
                    status=r.status,
                    started_at=r.started_at,
                    finished_at=r.finished_at,
                ).model_dump()
                for r in runs
            ],
            "total": len(runs),
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Trigger.dev error: {e}")


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str) -> dict[str, str]:
    """Cancel a queued or in-progress run."""
    config = TriggerConfig()
    if not config.is_configured:
        raise HTTPException(status_code=503, detail="Trigger.dev not configured.")

    client = _get_client()
    try:
        await client.cancel_run(run_id)
        return {"status": "cancelled", "run_id": run_id}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Trigger.dev error: {e}")


@router.get("/schedules", response_model=ScheduleStatusResponse)
async def get_schedule_status() -> ScheduleStatusResponse:
    """Get status of all managed schedules."""
    config = TriggerConfig()
    if not config.is_configured:
        raise HTTPException(status_code=503, detail="Trigger.dev not configured.")

    scheduler = _get_scheduler()
    try:
        status = await scheduler.get_status()
        return ScheduleStatusResponse(**status)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Trigger.dev error: {e}")


@router.post("/schedules/sync")
async def sync_schedules() -> dict[str, Any]:
    """Sync all task schedules with Trigger.dev (idempotent)."""
    config = TriggerConfig()
    if not config.is_configured:
        raise HTTPException(status_code=503, detail="Trigger.dev not configured.")

    scheduler = _get_scheduler()
    try:
        results = await scheduler.sync_all()
        return {
            "synced": len(results),
            "schedules": {
                task_id: {"id": handle.id, "cron": handle.cron}
                for task_id, handle in results.items()
            },
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Trigger.dev error: {e}")


@router.post("/schedules/deactivate-all")
async def deactivate_all_schedules() -> dict[str, int]:
    """Deactivate all managed schedules (emergency stop)."""
    config = TriggerConfig()
    if not config.is_configured:
        raise HTTPException(status_code=503, detail="Trigger.dev not configured.")

    scheduler = _get_scheduler()
    count = await scheduler.deactivate_all()
    return {"deactivated": count}


@router.post("/schedules/activate-all")
async def activate_all_schedules() -> dict[str, int]:
    """Activate all managed schedules."""
    config = TriggerConfig()
    if not config.is_configured:
        raise HTTPException(status_code=503, detail="Trigger.dev not configured.")

    scheduler = _get_scheduler()
    count = await scheduler.activate_all()
    return {"activated": count}


@router.get("/config")
async def get_trigger_config() -> dict[str, Any]:
    """Get current Trigger.dev configuration (redacted)."""
    config = TriggerConfig()
    scheduled = get_scheduled_tasks()
    registry = get_task_registry()

    return {
        "configured": config.is_configured,
        "api_url": config.api_url,
        "project_ref": config.project_ref,
        "secret_key_set": bool(config.secret_key),
        "total_tasks": len(registry),
        "scheduled_tasks": len(scheduled),
        "categories": {
            cat.value: len(get_tasks_by_category(cat))
            for cat in TaskCategory
        },
    }
