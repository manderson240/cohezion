"""Cross-Session Event Bridge for Durable Inter-Session Agent Collaboration.
==========================================================================
Connects the local in-memory EventBus to SurrealDB `event_log` table,
enabling multi-agent cross-session event persistence, live broadcasts,
and inter-session collaboration cascades.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from cohezion.core.event_bus import Event, EventBus
from cohezion.core.persistence.surreal_client import SurrealClient


logger = logging.getLogger(__name__)


@dataclass
class CrossSessionEventBridge:
    """Intercepts EventBus events and persists bi-temporal records to SurrealDB event_log."""

    event_bus: EventBus
    session_id: str
    surreal_client: SurrealClient = field(default_factory=SurrealClient)
    _subscribed: bool = field(default=False, init=False)

    async def initialize(self) -> None:
        """Subscribe bridge to the local EventBus and ensure DB connection."""
        if not self._subscribed:
            self.event_bus.register_handler(self._on_local_event, event_type=None)
            self._subscribed = True
            logger.info("CrossSessionEventBridge subscribed to local EventBus for session: %s", self.session_id)

    async def _on_local_event(self, event: Event) -> None:
        """Persist local events to SurrealDB event_log for cross-session visibility."""
        record_id = f"evt_{self.session_id}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
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
                timeout=3.0,
            )
            logger.debug("Persisted cross-session event %s to event_log", record_id)
        except Exception as err:
            logger.warning("Failed to persist event to SurrealDB event_log: %s", err)

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
        """Synchronously dispatch event onto local bus and queue for persistence."""
        try:
            self.event_bus.publish_sync(event)
            return True
        except Exception as err:
            logger.warning("Failed sync dispatch on cross-session bridge: %s", err)
            return False
