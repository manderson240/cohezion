"""Durable SurrealDB write-through bridge for DataMesh domain events.

Every DataMesh EventType published to the global EventBus is persisted to the
`data_product_event` table in SurrealDB, giving agents a durable audit trail
and enabling replay-from-checkpoint recovery.

Architecture:
    EventBus (in-memory pub/sub)
        → DataMeshEventBridge (write-through subscriber)
            → SurrealDB data_product_event table (durable log)
                → replay_since() (recovery / catch-up reads)

Usage:
    async def setup():
        bus = await get_event_bus()
        bridge = DataMeshEventBridge()
        bridge.subscribe(bus)

    # Now all DataMesh events are automatically persisted.
    # After a restart, replay missed events:
    missed = bridge.replay_since(last_checkpoint_ts)
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from typing import Any

import httpx

from cohezion.core.event_bus import Event, EventBus, EventType


logger = logging.getLogger(__name__)

_SURREAL_URL = "http://127.0.0.1:8001/sql"
_SURREAL_AUTH = ("root", "root")
_SURREAL_HEADERS = {
    "surreal-ns": "cohezion",
    "surreal-db": "main",
    "Content-Type": "text/plain",
    "Accept": "application/json",
}


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class DataMeshEventBridge:
    """Write-through subscriber: persists every DataMesh event to SurrealDB.

    SurrealDB acts as the durable event backbone; the in-memory EventBus handles
    fan-out to live subscribers. This split avoids coupling agent reaction latency
    to database write latency — the bridge writes asynchronously while handlers
    execute concurrently.
    """

    TABLE = "data_product_event"

    SUBSCRIBED_TYPES: list[EventType] = [
        EventType.DATA_PRODUCT_CREATED,
        EventType.DATA_PRODUCT_UPDATED,
        EventType.DATA_PRODUCT_QUALITY_ALERT,
        EventType.LINEAGE_UPDATED,
        EventType.DOMAIN_HEALTH_DEGRADED,
        EventType.CUSTOM,  # GAP-5: persist GaiaDataAgent HEAL/ALERT/ENRICH decisions
    ]

    def __init__(
        self,
        surreal_url: str = _SURREAL_URL,
        timeout: float = 5.0,
    ) -> None:
        self._surreal_url = surreal_url
        self._timeout = timeout
        self._http = httpx.Client(timeout=timeout)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create the data_product_event table schema once."""
        ddl = f"""
        DEFINE TABLE IF NOT EXISTS {self.TABLE} SCHEMAFULL;
        DEFINE FIELD IF NOT EXISTS event_type ON {self.TABLE} TYPE string;
        DEFINE FIELD IF NOT EXISTS source      ON {self.TABLE} TYPE string;
        DEFINE FIELD IF NOT EXISTS timestamp   ON {self.TABLE} TYPE float;
        DEFINE FIELD IF NOT EXISTS payload     ON {self.TABLE} TYPE string;
        DEFINE FIELD IF NOT EXISTS priority    ON {self.TABLE} TYPE int;
        DEFINE INDEX IF NOT EXISTS idx_ts ON {self.TABLE} FIELDS timestamp;
        """
        try:
            self._http.post(
                self._surreal_url,
                content=ddl,
                headers=_SURREAL_HEADERS,
                auth=_SURREAL_AUTH,
                timeout=10.0,
            )
            logger.debug("DataMeshEventBridge schema ensured")
        except Exception as exc:
            logger.debug("DataMeshEventBridge schema setup failed (non-fatal): %s", exc)

    def subscribe(self, bus: EventBus) -> None:
        """Register this bridge as a handler on the given EventBus.

        Each DataMesh EventType gets its own subscription slot so the bus
        can track handler counts per type correctly. Uses the public
        register_handler() API (GAP-4) rather than direct _handlers access.
        """
        for event_type in self.SUBSCRIBED_TYPES:
            bus.register_handler(self._handle, event_type)

    async def _handle(self, event: Event) -> None:
        """Persist a single DataMesh event to SurrealDB."""
        # Guard against raw-interpolation SQL injection: Event annotations are not
        # enforced at runtime, so a caller can pass a string for timestamp/priority.
        # float()/int() either normalise a valid value or raise — in which case we
        # drop the event at DEBUG rather than embed unsanitised SQL.
        try:
            ts = float(event.timestamp)
            pri = int(event.priority)
        except (TypeError, ValueError) as exc:
            logger.debug("DataMeshEventBridge: invalid numeric field, dropping event: %s", exc)
            return

        payload_json = _escape(json.dumps(event.payload))
        sql = (
            f"CREATE {self.TABLE} SET "
            f'event_type = "{event.type.name}", '
            f'source = "{_escape(event.source)}", '
            f"timestamp = {ts}, "
            f'payload = "{payload_json}", '
            f"priority = {pri};"
        )
        try:
            self._http.post(
                self._surreal_url,
                content=sql,
                headers=_SURREAL_HEADERS,
                auth=_SURREAL_AUTH,
            )
        except Exception as exc:
            logger.debug("DataMeshEventBridge write failed (non-fatal): %s", exc)

    def replay_since(self, since_ts: float) -> list[dict[str, Any]]:
        """Return all persisted DataMesh events with timestamp > since_ts.

        Used for catch-up reads after a restart or missed-event recovery.
        Events are returned in ascending timestamp order.

        Args:
            since_ts: Unix timestamp (float). Only events AFTER this point are returned.

        Returns:
            List of raw row dicts: {event_type, source, timestamp, payload, priority}
        """
        sql = (
            f"SELECT event_type, source, timestamp, payload, priority "
            f"FROM {self.TABLE} "
            f"WHERE timestamp > {since_ts} "
            f"ORDER BY timestamp ASC;"
        )
        try:
            resp = self._http.post(
                self._surreal_url,
                content=sql,
                headers=_SURREAL_HEADERS,
                auth=_SURREAL_AUTH,
            )
            results = resp.json()
            if isinstance(results, list) and results:
                rows = results[0].get("result", [])
                out = []
                for row in rows:
                    with contextlib.suppress(json.JSONDecodeError, TypeError):
                        row["payload"] = json.loads(row.get("payload", "{}"))
                    out.append(row)
                return out
        except Exception as exc:
            logger.debug("DataMeshEventBridge.replay_since failed: %s", exc)
        return []

    async def watch_federation(
        self,
        federation: object,
        poll_interval_s: float = 30.0,
        products: object | None = None,
    ) -> None:
        """Poll FederationLayer health and publish DOMAIN_HEALTH_DEGRADED events.

        Designed to run as a cancellable asyncio.Task:
            task = asyncio.create_task(bridge.watch_federation(fed, poll_interval_s=30.0))
            ...
            task.cancel()

        On each poll:
        - If a previously-healthy domain becomes unhealthy, publishes DOMAIN_HEALTH_DEGRADED.
        - If products dict is provided (GAP-3), checks each DataProduct.meets_sla and
          publishes DATA_PRODUCT_QUALITY_ALERT for any that are violating their SLA.

        Args:
            federation: A FederationLayer instance (typed as object to allow lazy import).
            poll_interval_s: Seconds between health polls.
            products: Optional dict[str, DataProduct] of inference products to poll for SLA.
        """
        from cohezion.core.event_bus import Event, EventType, get_event_bus

        bus = await get_event_bus()
        prev_health: dict[str, bool] = {}
        first_poll = True

        while True:
            try:
                health: dict[str, bool] = await federation.health_check()  # type: ignore[union-attr]
                for domain, healthy in health.items():
                    was_healthy = prev_health.get(domain, True)
                    if first_poll:
                        pass
                    elif was_healthy and not healthy:
                        event = Event(
                            type=EventType.DOMAIN_HEALTH_DEGRADED,
                            source="DataMeshEventBridge.watch_federation",
                            payload={"domain": domain, "status": "unhealthy"},
                        )
                        await bus.publish(event)
                        logger.warning(
                            "watch_federation: domain %r became unhealthy — event published",
                            domain,
                        )
                    elif not was_healthy and healthy:
                        logger.info("watch_federation: domain %r recovered", domain)
                prev_health = health
                first_poll = False
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.debug("watch_federation poll failed (non-fatal): %s", exc)

            # GAP-3: proactively poll inference product SLAs
            if products:
                try:
                    for product in products.values():  # type: ignore[union-attr]
                        if not product.meets_sla:
                            sla_event = Event(
                                type=EventType.DATA_PRODUCT_QUALITY_ALERT,
                                source="DataMeshEventBridge.watch_federation",
                                payload={
                                    "product_id": product.product_id,
                                    "name": product.name,
                                    "domain": product.owner_domain,
                                    "error_rate": product.error_rate,
                                    "meets_sla": False,
                                    "reason": "SLA violated (proactive poll)",
                                },
                            )
                            await bus.publish(sla_event)
                            logger.warning(
                                "watch_federation: SLA violation for product %r (error_rate=%.3f)",
                                product.product_id,
                                product.error_rate,
                            )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.debug("watch_federation SLA poll failed (non-fatal): %s", exc)

            await asyncio.sleep(poll_interval_s)


def make_event_bridge() -> DataMeshEventBridge | None:
    """Factory — returns None if SurrealDB is unreachable."""
    try:
        bridge = DataMeshEventBridge()
        logger.info("DataMeshEventBridge ready")
        return bridge
    except Exception as exc:
        logger.debug("DataMeshEventBridge unavailable: %s", exc)
        return None
