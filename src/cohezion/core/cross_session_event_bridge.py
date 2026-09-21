"""Cross-Session Event Bridge for Durable Inter-Session Agent Collaboration.
==========================================================================
Connects the local in-memory EventBus to SurrealDB `event_log` table,
enabling multi-agent cross-session event persistence, live broadcasts,
and inter-session collaboration cascades.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

from cohezion.core.event_bus import Event, EventBus
from cohezion.core.persistence.surreal_client import SurrealClient


logger = logging.getLogger(__name__)

_EVENT_HANDLER_TIMEOUT_S = float(os.environ.get("EVENT_HANDLER_TIMEOUT_S", "3.0"))


@dataclass
class CrossSessionEventBridge:
    """Intercepts EventBus events and persists bi-temporal records to SurrealDB event_log."""

    event_bus: EventBus
    session_id: str
    surreal_client: SurrealClient = field(default_factory=SurrealClient)
    _subscribed: bool = field(default=False, init=False)
    _sync_loop: Any = field(default=None, init=False, repr=False)
    # Strong refs to in-loop persist tasks: the loop holds only weak refs, so an
    # un-retained task can be garbage-collected mid-flight.
    _pending_persist: set[asyncio.Task[bool]] = field(default_factory=set, init=False, repr=False)
    # Why events cannot reach event_log, once known (probe at initialize, or a failed write).
    # None = no known problem. While set, publish_and_persist reports False instead of True.
    persistence_error: str | None = field(default=None, init=False)

    async def initialize(self) -> None:
        """Subscribe bridge to the local EventBus and ensure DB connection.

        Probes persistence once. Until 2026-09-21 a session without SurrealDB credentials got
        True from every publish_and_persist while the client refused every write, and the only
        signal was a per-event warning.
        """
        if not self._subscribed:
            self.event_bus.register_handler(self._on_local_event, event_type=None)
            self._subscribed = True
            logger.info(
                "CrossSessionEventBridge subscribed to local EventBus for session: %s",
                self.session_id,
            )
        try:
            await asyncio.wait_for(
                self.surreal_client.query("RETURN 1;", {}), timeout=_EVENT_HANDLER_TIMEOUT_S
            )
            self.persistence_error = None
        except Exception as err:
            self._record_persistence_error(err)

    def _record_persistence_error(self, err: BaseException) -> None:
        first = self.persistence_error is None
        self.persistence_error = f"{type(err).__name__}: {err}"
        if first:
            logger.error(
                "CrossSessionEventBridge (session %s) CANNOT persist to event_log -- events stay "
                "in this process and publish_and_persist returns False until a write succeeds. "
                "Cause: %s",
                self.session_id,
                self.persistence_error,
            )

    def _record_id(self, event: Event) -> str:
        """Deterministic record id so at-least-once delivery cannot duplicate rows."""
        digest = hashlib.sha256(
            f"{self.session_id}|{event.type.name}|{event.source}|{event.timestamp!r}".encode()
        ).hexdigest()[:16]
        return f"evt_{self.session_id}_{digest}"

    async def _persist(self, event: Event) -> bool:
        """UPSERT one event into event_log. True only on a confirmed write."""
        record_id = self._record_id(event)
        event_data = {
            "type": event.type.name,
            "source": event.source,
            "session_id": self.session_id,
            "timestamp": event.timestamp,
            "payload": event.payload,
            "priority": event.priority,
            "valid_from": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(event.timestamp)),
            "valid_to": None,
        }

        try:
            await asyncio.wait_for(
                self.surreal_client.query(
                    "UPSERT type::record('event_log', $record_id) CONTENT $data;",
                    {"record_id": record_id, "data": event_data},
                ),
                timeout=_EVENT_HANDLER_TIMEOUT_S,
            )
            logger.debug("Persisted cross-session event %s to event_log", record_id)
            self.persistence_error = None
            return True
        except TimeoutError:
            logger.error(
                "Event persistence timed out after %.1fs -- event %s/%s LOST from event_log",
                _EVENT_HANDLER_TIMEOUT_S,
                event.type.name,
                event.source,
            )
            return False
        except Exception as err:
            logger.warning("Failed to persist event to SurrealDB event_log: %s", err)
            self._record_persistence_error(err)
            return False

    async def _on_local_event(self, event: Event) -> None:
        """Persist local events to SurrealDB event_log for cross-session visibility."""
        await self._persist(event)

    async def fetch_cross_session_events(
        self, target_event_type: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Fetch recent cross-session events published by other active agent sessions via parameterized SurrealQL."""
        bindings: dict[str, Any] = {"session_id": self.session_id, "limit": limit}

        if target_event_type:
            sql = "SELECT * FROM event_log WHERE session_id != $session_id AND type = $target_type ORDER BY timestamp DESC LIMIT $limit;"
            bindings["target_type"] = target_event_type
        else:
            sql = "SELECT * FROM event_log WHERE session_id != $session_id ORDER BY timestamp DESC LIMIT $limit;"

        try:
            res = await self.surreal_client.query(sql, bindings)
            if isinstance(res, list) and len(res) > 0 and "result" in res[0]:
                return res[0]["result"]
            return []
        except Exception as err:
            logger.warning("Failed to fetch cross-session events: %s", err)
            return []

    def publish_and_persist(self, event: Event) -> bool:
        """Dispatch onto the local bus AND persist the event.

        Two contexts, two meanings of True:

        * Sync context (no running loop): persistence is driven here on a
          reusable loop; True only if the event reached ``event_log``.
        * Inside a running loop the write cannot block, so it is scheduled.
          True means "dispatched to a RUNNING bus; persistence scheduled" --
          NOT persisted. A failed write is logged as a warning (by ``_persist``,
          or by the task's done-callback if the task itself raised). False if
          the bus is not running (mirrors ``EventBus.publish``, D7): an event
          ``put_nowait`` into an undrained queue is the original defect.

        The deterministic record id keeps a scheduled write idempotent with the
        subscriber's.
        """
        try:
            asyncio.get_running_loop()
            in_loop = True
        except RuntimeError:
            in_loop = False

        if in_loop and not self.event_bus._running:
            logger.warning("publish_and_persist refused: event bus is not running")
            return False

        try:
            dispatched = bool(self.event_bus.publish_sync(event))
        except Exception as err:
            logger.warning("Failed sync dispatch on cross-session bridge: %s", err)
            dispatched = False

        if not in_loop:
            # One reusable loop per bridge: SurrealClient caches a connection bound
            # to the loop that created it, so asyncio.run() (a fresh loop per call)
            # fails every call after the first with "attached to a different loop".
            if self._sync_loop is None or self._sync_loop.is_closed():
                self._sync_loop = asyncio.new_event_loop()
            # bool() is a narrowing, not a silencer: _sync_loop is typed Any (it holds an
            # AbstractEventLoop created lazily), so run_until_complete returns Any even
            # though _persist is declared -> bool.
            return bool(self._sync_loop.run_until_complete(self._persist(event)))

        task = asyncio.ensure_future(self._persist(event))
        self._pending_persist.add(task)
        task.add_done_callback(self._on_persist_done)
        # Persistence already known broken: still dispatched locally (and the write is retried,
        # which clears the error on success), but cross-session delivery must not be claimed.
        return dispatched and self.persistence_error is None

    def _on_persist_done(self, task: asyncio.Task[bool]) -> None:
        """Retire a scheduled persist task and surface any failure it would hide."""
        self._pending_persist.discard(task)
        if task.cancelled():
            logger.warning("Scheduled cross-session persist task was cancelled")
            return
        err = task.exception()
        if err is not None:
            logger.warning("Scheduled cross-session persist task failed: %s", err)
