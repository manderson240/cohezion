"""Delegation Logger for Cohezion Proactive Hybrid Router.

Logs all model routing and escalation events (EVI calculations, quality gaps, costs)
to SurrealDB `delegation_log` table and local fallback store.

Outcome telemetry (Dream-RSI): ``log_delegation`` records the DECISION inputs
only (EVI score, tiers, model, reason). The perpetual proactive-loop consumer
should call :meth:`DelegationLogger.log_outcome` when a delegation completes
so the SAME SurrealDB row gains its realized outcome (quality score, cost,
succeeded verdict) that ``cohezion.agi.dream_rsi`` replays against.
``log_outcome`` is optional and no-op-safe: with nothing to record it makes
no HTTP call, and a failed SurrealDB write logs a warning and returns
``False`` (fail-open) — the decision row survives regardless.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import threading
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

FALLBACK_LOG_PATH = Path.home() / ".cohezion" / "delegation_log.jsonl"


def _surreal_basic_auth() -> str:
    """Basic-auth header value (``Basic <b64>``) for the local SurrealDB.

    ``SURREAL_USER``/``SURREAL_PASS`` env override with the historical dev
    default ``root:root``; shared source of truth with
    ``cohezion.data_mesh.kanban_bridge._surreal_basic_auth``. Replaces the
    hardcoded ``root:root`` that review flagged (2026-09-14).
    """
    import os

    user = os.environ.get("SURREAL_USER", "root")
    password = os.environ.get("SURREAL_PASS", "root")
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


@dataclass
class DelegationEvent:
    """Record of an escalation or routing delegation decision."""

    task_name: str
    task_importance: float  # Scale 0.0 - 1.0
    quality_gap: float  # Scale 0.0 - 1.0
    escalation_cost: float  # Relative cost unit (> 0)
    evi_score: float  # Computed EVI score
    source_tier: int  # 1 (Local), 2 (Ollama Cloud), 3 (Premium API)
    target_tier: int  # 1, 2, or 3
    escalated: bool  # True if tier increased
    model_selected: str
    reason: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary representation."""
        return asdict(self)


class DelegationLogger:
    """Non-blocking logger for hybrid delegation and escalation events."""

    def __init__(
        self,
        surreal_url: str = "http://localhost:8001",
        db_ns: str = "cohezion",
        db_name: str = "main",
    ) -> None:
        self.surreal_url = surreal_url.rstrip("/")
        self.db_ns = db_ns
        self.db_name = db_name
        self.fallback_path = FALLBACK_LOG_PATH
        self.fallback_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def log_delegation(self, event: DelegationEvent) -> None:
        """Log delegation event asynchronously without blocking caller."""
        event_dict = event.to_dict()

        # Capture the caller's running loop (if any) so the daemon thread can
        # schedule the EventBus publish back onto it via
        # asyncio.run_coroutine_threadsafe (docs.python.org/3/library/
        # asyncio-dev.html: coroutines are scheduled cross-thread only through
        # this API). A private/private loop would deliver to nobody.
        try:
            caller_loop = asyncio.get_running_loop()
        except RuntimeError:
            caller_loop = None

        # Local JSONL file fallback (thread-safe, persistent)
        try:
            with self._lock, open(self.fallback_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event_dict) + "\n")
                f.flush()
        except Exception as exc:
            logger.warning("Failed to write local delegation log: %s", exc)

        # Asynchronous SurrealDB push + EventBus & Kanban integration
        def _surreal_and_mesh_push() -> None:
            # 1. SurrealDB SQL push
            sql = f"CREATE delegation_log CONTENT {json.dumps(event_dict)};"
            req = urllib.request.Request(
                f"{self.surreal_url}/sql",
                data=sql.encode("utf-8"),
                headers={
                    "Accept": "application/json",
                    "surreal-ns": self.db_ns,
                    "surreal-db": self.db_name,
                    "Authorization": _surreal_basic_auth(),
                },
                method="POST",
            )
            try:
                urllib.request.urlopen(req, timeout=2)
            except Exception as exc:
                logger.debug("SurrealDB delegation_log push offline: %s", exc)

            # 2. EventBus Event publishing — through the shared auto-starting
            #    singleton, scheduled back onto the CALLER's running loop with
            #    asyncio.run_coroutine_threadsafe. This daemon thread has no
            #    event loop: get_event_loop() raises, create_task is
            #    impossible, and a private asyncio.run() loop would deliver to
            #    nobody. With no caller loop (sync context), publishing is
            #    skipped — SurrealDB + JSONL already carry the record.
            try:
                from cohezion.core.event_bus import Event, EventType, get_event_bus

                ev = Event(
                    type=EventType.METRIC_UPDATE,
                    source="unified_hybrid_router",
                    payload=event_dict,
                )

                async def _publish_metric_update() -> None:
                    bus = await get_event_bus()
                    await bus.publish(ev)

                if caller_loop is not None and caller_loop.is_running():
                    asyncio.run_coroutine_threadsafe(_publish_metric_update(), caller_loop)
            except Exception as exc:
                logger.debug("EventBus publishing non-blocking exception: %s", exc)

            # 3. Agentic Kanban Card persistence on escalation events
            if event.escalated:
                try:
                    from cohezion.data_mesh.kanban_bridge import persist_item

                    card_id = f"escalate_{event.task_name}_{int(event.timestamp)}"
                    persist_item(
                        {
                            "id": card_id,
                            "title": f"[Tier Escalation] {event.task_name}: Tier {event.source_tier} -> Tier {event.target_tier} ({event.model_selected})",
                            "status": "in_progress",
                            "priority": "high" if event.target_tier == 3 else "medium",
                            "source": "inference/hybrid_router",
                            "category": "tier_escalation",
                            "notes": f"EVI Score: {event.evi_score:.4f} | Reason: {event.reason}",
                        }
                    )
                except Exception as exc:
                    logger.debug("Kanban bridge persistence non-blocking exception: %s", exc)

        threading.Thread(target=_surreal_and_mesh_push, daemon=True).start()

    def log_outcome(
        self,
        delegation_id: str,
        *,
        quality_score: float | None = None,
        cost_seconds: float | None = None,
        succeeded: bool | None = None,
        error: str | None = None,
    ) -> bool:
        """Record a completed delegation's outcome on its EXISTING log row.

        Called by the perpetual proactive-loop consumer when a delegation
        finishes; UPDATES (MERGE) the row ``log_delegation`` created rather
        than inserting a new one. ``delegation_id`` is the SurrealDB record id
        of that row — ``log_delegation`` does not currently return one, so
        callers that can pin an id (e.g. by CREATEing with a deterministic id)
        should pass it here; a bare table-name-less id string is accepted.

        Column naming is pinned to the ``cohezion.agi.dream_rsi`` loader
        contract (``_record_from_row`` + ``OUTCOME_KEYS``):

        * ``metrics`` — a mapping whose ``score`` entry lands directly in
          ``outcome_metrics`` where ``OUTCOME_KEYS`` looks first (a bare
          top-level ``score`` column would be swallowed by
          ``_SCALAR_CONTEXT_EXCLUDE`` and become invisible to the loader);
        * ``cost`` — numeric seconds, mapped to ``DiscoveryRecord.cost``;
        * ``succeeded`` — bool, mapped to ``DiscoveryRecord.succeeded``;
        * ``outcome_error`` — string error text, kept out of the scalar
          outcome columns (excluded from ``outcome_metrics`` because it is a
          non-numeric field) and readable as context.

        Optional and no-op-safe: with nothing to record it performs no HTTP,
        and a failed SurrealDB write logs a warning and returns ``False``
        (fail-open) — never raises. Returns ``True`` when the update was
        dispatched (and parsed OK when a response is readable).

        Note: the local JSONL fallback file is not updated (the decision row
        there has no stable record id to merge onto); SurrealDB is the
        outcome channel.
        """
        metrics: dict[str, float] = {}
        if quality_score is not None:
            metrics["score"] = float(quality_score)
        if not metrics and cost_seconds is None and succeeded is None and error is None:
            return True  # nothing to record — no-op, no HTTP

        updates: dict[str, Any] = {}
        if metrics:
            updates["metrics"] = metrics
        if cost_seconds is not None:
            updates["cost"] = float(cost_seconds)
        if succeeded is not None:
            updates["succeeded"] = bool(succeeded)
        if error is not None:
            updates["outcome_error"] = str(error)

        # SurrealDB record ids with non-alphanumeric chars need backtick
        # quoting (kanban_bridge pattern).
        safe_id = delegation_id if delegation_id.isalnum() else f"`{delegation_id}`"
        sql = f"UPDATE delegation_log:{safe_id} MERGE {json.dumps(updates)};"

        try:
            req = urllib.request.Request(  # noqa: S310
                f"{self.surreal_url}/sql",
                data=sql.encode("utf-8"),
                headers={
                    "Accept": "application/json",
                    "surreal-ns": self.db_ns,
                    "surreal-db": self.db_name,
                    "Authorization": _surreal_basic_auth(),
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=2) as resp:  # noqa: S310
                body = json.loads(resp.read())
            if isinstance(body, list):
                failed = [e for e in body if isinstance(e, dict) and e.get("status") != "OK"]
                if failed:
                    logger.warning("SurrealDB delegation_log outcome merge failed: %s", failed)
                    return False
            return True
        except Exception as exc:
            # Fail-open: outcome telemetry must never break the caller's loop.
            logger.warning("SurrealDB delegation_log outcome push offline: %s", exc)
            return False

    def get_recent_events(self, limit: int = 20) -> list[dict[str, Any]]:
        """Read recent delegation events: SurrealDB first, JSONL fallback second.

        The write path targets the `delegation_log` table in SurrealDB; the
        original reader consumed only the JSONL fallback file, which made the
        DB table write-only (2,155 rows with no reader at audit time).
        """
        # 1. SurrealDB primary read (mirrors the write path's auth + headers)
        try:
            sql = f"SELECT * FROM delegation_log ORDER BY timestamp DESC LIMIT {limit};"
            req = urllib.request.Request(
                f"{self.surreal_url}/sql",
                method="POST",
                data=sql.encode("utf-8"),
                headers={
                    "Accept": "application/json",
                    "surreal-ns": self.db_ns,
                    "surreal-db": self.db_name,
                    "Authorization": _surreal_basic_auth(),
                },
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                body = json.loads(resp.read())
            rows: list[dict[str, Any]] = []
            if isinstance(body, list):
                for entry in body:
                    if isinstance(entry, dict) and entry.get("status") == "OK":
                        result = entry.get("result")
                        if isinstance(result, list):
                            rows.extend(result)
            if rows:
                return rows
            logger.debug("SurrealDB delegation_log read returned 0 rows; using JSONL fallback")
        except Exception as exc:
            logger.debug("SurrealDB delegation_log read offline: %s", exc)

        # 2. Local JSONL file fallback (original behavior)
        if not self.fallback_path.exists():
            return []
        events = []
        try:
            with open(self.fallback_path, encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    if line.strip():
                        events.append(json.loads(line))
        except Exception as exc:
            logger.error("Error reading delegation logs: %s", exc)
        # Match the DB path's ordering (ORDER BY timestamp DESC) so callers
        # get the same sequence regardless of which path served the rows.
        events.sort(key=lambda e: e.get("timestamp", 0), reverse=True)
        return events
