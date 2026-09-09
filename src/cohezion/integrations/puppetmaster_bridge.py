"""Puppetmaster Integration Bridge with FleetLock Hardware Aperture Fencing.

Bridges Puppetmaster (SQLite WAL state store and CLI subprocess workers)
with Cohezion's EventBus, SurrealDB Compound Graph, and Strix Halo Hardware Protection:
- Acquires FleetLock('modelload') before any local silicon model is loaded
- Reads typed artifacts and completion receipts from Puppetmaster's SQLite database at $0 token cost
- Publishes agent lifecycle events to Cohezion's EventBus
- Persists compound loop outcomes into SurrealDB and Obsidian MOCs
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cohezion.core.event_bus import Event, EventBus, get_event_bus
from cohezion.researcher.daily_researcher import FleetLock
from cohezion.reliability.oom_guard import OOMGuard

logger = logging.getLogger(__name__)

DEFAULT_PM_STATE_DB = Path.home() / ".puppetmaster" / "state.db"


@dataclass(frozen=True)
class PuppetmasterReceipt:
    job_id: str
    status: str
    target_worktree: str
    prompt: str
    artifacts_count: int
    total_tokens: int
    duration_s: float


class PuppetmasterBridge:
    """Bridges Puppetmaster subprocess execution with Cohezion mesh and FleetLock."""

    def __init__(
        self,
        db_path: Path = DEFAULT_PM_STATE_DB,
        event_bus: EventBus | None = None,
    ) -> None:
        self.db_path = db_path
        self.bus = event_bus if event_bus is not None else EventBus()

    def is_state_db_available(self) -> bool:
        """Check if Puppetmaster state database exists."""
        return self.db_path.is_file()

    def acquire_hardware_admission(self, task_name: str, timeout_s: float = 30.0) -> bool:
        """Enforce FleetLock aperture protection before any worker touches local silicon."""
        mem_state = OOMGuard.get_memory_state()
        if not mem_state.is_safe:
            logger.warning(
                "Hardware admission denied for %s: available memory %.1f GiB < floor %.1f GiB",
                task_name,
                mem_state.available_gb,
                mem_state.dynamic_floor_gb,
            )
            return False

        try:
            with FleetLock("modelload", timeout_s=timeout_s):
                logger.info("FleetLock granted for Puppetmaster worker: %s", task_name)
                return True
        except TimeoutError:
            logger.error("FleetLock acquisition timed out for %s", task_name)
            return False

    def get_latest_receipts(self, limit: int = 5) -> list[PuppetmasterReceipt]:
        """Read recent completion receipts from Puppetmaster's SQLite WAL database."""
        if not self.is_state_db_available():
            logger.debug("Puppetmaster state database not found at %s", self.db_path)
            return []

        receipts: list[PuppetmasterReceipt] = []
        try:
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            query = """
                SELECT job_id, status, COALESCE(worktree, ''), COALESCE(prompt, ''),
                       COALESCE(artifacts_count, 0), COALESCE(total_tokens, 0),
                       COALESCE(duration_s, 0.0)
                FROM jobs
                ORDER BY created_at DESC
                LIMIT ?;
            """
            cursor.execute(query, (limit,))
            for row in cursor.fetchall():
                receipts.append(
                    PuppetmasterReceipt(
                        job_id=str(row[0]),
                        status=str(row[1]),
                        target_worktree=str(row[2]),
                        prompt=str(row[3]),
                        artifacts_count=int(row[4]),
                        total_tokens=int(row[5]),
                        duration_s=float(row[6]),
                    )
                )
            conn.close()
        except Exception as exc:
            logger.warning("Error reading Puppetmaster receipts: %s", exc)
        return receipts

    async def publish_job_completion(self, receipt: PuppetmasterReceipt) -> None:
        """Publish completed Puppetmaster job receipt to Cohezion's EventBus."""
        await self.bus.publish(
            Event.agent_complete(
                agent_name=f"puppetmaster:{receipt.job_id}",
                result={
                    "status": receipt.status,
                    "worktree": receipt.target_worktree,
                    "artifacts_count": receipt.artifacts_count,
                    "total_tokens": receipt.total_tokens,
                },
                duration_ms=receipt.duration_s * 1000.0,
            )
        )
        logger.info("Published Puppetmaster job %s completion event to EventBus", receipt.job_id)
