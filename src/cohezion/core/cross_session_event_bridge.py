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

    async def initialize(self) -> None:
        """Subscribe bridge to the local EventBus and ensure DB connection."""
        if not self._subscribed:
            self.event_bus.register_handler(self._on_local_event, event_type=None)
            self._subscribed = True
            logger.info(
                "CrossSessionEventBridge subscribed to local EventBus for session: %s",
                self.session_id,
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
        """Dispatch onto the local bus AND durably persist the event.

        ``publish_sync`` only enqueues; with no running bus nothing drains the
        queue, so persistence is driven here rather than left to the subscriber.
        Returns True only when the event reached ``event_log``. Inside a running
        loop the write cannot block, so it is scheduled and the dispatch result is
        returned; the deterministic record id keeps that write idempotent with the
        subscriber's.
        """
        try:
            dispatched = bool(self.event_bus.publish_sync(event))
        except Exception as err:
            logger.warning("Failed sync dispatch on cross-session bridge: %s", err)
            dispatched = False

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # One reusable loop per bridge: SurrealClient caches a connection bound
            # to the loop that created it, so asyncio.run() (a fresh loop per call)
            # fails every call after the first with "attached to a different loop".
            if self._sync_loop is None or self._sync_loop.is_closed():
                self._sync_loop = asyncio.new_event_loop()
            # bool() is a narrowing, not a silencer: _sync_loop is typed Any (it holds an
            # AbstractEventLoop created lazily), so run_until_complete returns Any even
            # though _persist is declared -> bool.
            return bool(self._sync_loop.run_until_complete(self._persist(event)))

        asyncio.ensure_future(self._persist(event))
        return dispatched
