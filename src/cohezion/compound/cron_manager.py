"""Cron job management for Cohezion compound engineering system.

Provides a thin wrapper around CronCreate/CronList/CronDelete for scheduling
recurring system health checks, quality digests, and silicon status polls.

All scheduled jobs are session-scoped (die when Claude exits) unless
persisted externally.

Usage:
    from cohezion.compound.cron_manager import CronManager
    cm = CronManager()
    cm.schedule_standard_jobs()
    cm.status()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime


logger = logging.getLogger(__name__)


@dataclass
class CronJob:
    """Metadata for a scheduled cron job."""

    job_id: str
    name: str
    description: str
    cron_expression: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class CronManager:
    """Manage session-scoped cron jobs for Cohezion system health.

    In Claude Code, CronCreate/CronDelete are available via the tool API.
    This manager tracks which jobs are registered and provides status reporting.

    Note: CronCreate is a Claude Code tool — CronManager tracks IDs but
    the actual scheduling happens via the Claude Code host. When running
    outside of Claude Code (e.g., in tests or scripts), scheduling is a no-op.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, CronJob] = {}

    def register(self, job_id: str, name: str, description: str, cron_expr: str) -> None:
        """Register a job that was scheduled via CronCreate."""
        self._jobs[job_id] = CronJob(
            job_id=job_id,
            name=name,
            description=description,
            cron_expression=cron_expr,
        )
        logger.info("CronManager: registered job %s (%s)", job_id, name)

    def cancel(self, job_id: str) -> None:
        """Remove a job from tracking (actual cancel must be done via CronDelete)."""
        self._jobs.pop(job_id, None)

    def cancel_all(self) -> list[str]:
        """Return all job IDs for cancellation via CronDelete, then clear registry."""
        ids = list(self._jobs.keys())
        self._jobs.clear()
        logger.info("CronManager: cleared %d jobs from registry", len(ids))
        return ids

    def status(self) -> dict[str, object]:
        """Return current job status summary."""
        return {
            "active_jobs": len(self._jobs),
            "jobs": [
                {
                    "id": j.job_id,
                    "name": j.name,
                    "cron": j.cron_expression,
                    "description": j.description,
                    "created": j.created_at.isoformat(),
                }
                for j in self._jobs.values()
            ],
        }

    def get_ids(self) -> list[str]:
        return list(self._jobs.keys())

    def __len__(self) -> int:
        return len(self._jobs)


def schedule_standard_jobs(manager: CronManager | None = None) -> list[str]:
    """Register the 4 standard Phase 13A system jobs into a CronManager.

    Returns the list of registered job IDs. Does NOT call CronCreate —
    that is a Claude Code tool and must be called separately in an
    interactive session. This function only updates the in-memory registry.
    """
    if manager is None:
        manager = _DEFAULT_MANAGER
    for job in STANDARD_JOBS:
        manager.register(
            job_id=job["name"],
            name=job["name"],
            description=job["description"],
            cron_expr=job["cron"],
        )
    return manager.get_ids()


_DEFAULT_MANAGER = CronManager()


# Standard job definitions (scheduled externally via CronCreate)
STANDARD_JOBS = [
    {
        "name": "npu-liveness",
        "description": "Check NPU liveness every 5 min; log if down",
        "cron": "*/5 * * * *",
        "prompt": (
            "Check NPU liveness: from cohezion.compound.local_inference import lemonade_available; "
            "up = lemonade_available(); print('NPU:', 'UP' if up else 'DOWN'); "
            "if not up: print('Action needed: lemond --port 13306 &')"
        ),
    },
    {
        "name": "autodqa-digest",
        "description": "Send AUTODQA quality digest via Telegram every hour",
        "cron": "23 * * * *",
        "prompt": (
            "Run AUTODQA digest: from cohezion.compound.cohezion_state import get_full_state; "
            "from cohezion.compound.telegram_notify import notify; "
            "s = get_full_state(); "
            'notify(f\'Cohezion state: NPU={s["silicon"]["npu_up"]} | AUTODQA={s["autodqa"]}\')'
        ),
    },
    {
        "name": "autoresearch-loop",
        "description": "Continue autoresearch experiments every 7 minutes",
        "cron": "*/7 * * * *",
        "prompt": (
            "Autoresearch loop: read autoresearch.md objective, check autoresearch.jsonl state, "
            "run next experiment, log result."
        ),
    },
    {
        "name": "experiential-distillation",
        "description": "Run the nightly Experiential Distillation pipeline for local model fine-tuning",
        "cron": "0 3 * * *",
        "prompt": (
            "Run DPO distillation: from cohezion.compound.distillation_pipeline import run_distillation; "
            "import asyncio; asyncio.run(run_distillation())"
        ),
    },
]
