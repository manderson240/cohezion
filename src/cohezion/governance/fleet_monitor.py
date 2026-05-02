"""
Fleet Monitor - Event-driven service monitoring for the Cohezion ecosystem.
Tracks ports, status, and health events across local hardware.
Supports Symphony-168 ephemeral test lanes.
"""

import asyncio
import logging
import os
import time
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from cohezion.core.event_bus import Event, EventType, get_event_bus
from cohezion.core.persistence.surreal_client import SurrealClient


logger = logging.getLogger(__name__)


class ServiceStatus(BaseModel):
    name: str
    port: int
    type: str  # 'systemd', 'process', 'container', 'ephemeral'
    health_url: str | None = None
    status: str = "unknown"
    last_check: datetime | None = None
    pid: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class FleetMonitor:
    """
    Monitors and manages the distributed fleet of Cohezion services.
    Uses SurrealDB Live Queries and EventBus for event-driven reactivity.
    """

    def __init__(self, db_client: SurrealClient | None = None):
        self.db = db_client or SurrealClient()
        self.services: dict[str, ServiceStatus] = {}
        self._monitor_task: asyncio.Task | None = None
        self._live_query_task: asyncio.Task | None = None
        self._running = False
        self.event_handlers: dict[str, list[callable]] = {}

    async def connect(self):
        """Connect to the database and load existing registry."""
        if not self.db._connected:
            await self.db.connect()

        # Load existing services from SurrealDB
        try:
            stored = await self.db.query("SELECT * FROM fleet_registry")
            if stored:
                for s in stored:
                    if isinstance(s, dict) and "name" in s:
                        self.services[s["name"]] = ServiceStatus(**s)
                        logger.info(
                            f"Loaded service '{s['name']}' from registry on port {s['port']}"
                        )
        except Exception as e:
            logger.warning(f"Failed to load fleet registry: {e}")

    async def _handle_live_event(self, event_data: dict[str, Any]):
        """Callback for SurrealDB Live Query events."""
        action = event_data.get("action")
        result = event_data.get("result", {})

        if action in ("CREATE", "UPDATE"):
            event_type = result.get("type")
            data = result.get("data", {})
            logger.info(f"🔔 Event Driven Trigger: {event_type}")

            if event_type in self.event_handlers:
                for handler in self.event_handlers[event_type]:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)

    async def subscribe_to_events(self):
        """Subscribe to live events from SurrealDB."""
        try:
            async for event in self.db.live("fleet_events"):
                await self._handle_live_event(event)
        except Exception as e:
            logger.error(f"Live Query failed: {e}")
            await asyncio.sleep(5)
            if self._running:
                asyncio.create_task(self.subscribe_to_events())

    def on(self, event_type: str, handler: callable):
        """Register a handler for a specific event type."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)

    async def emit_event(self, event_type: str, data: dict[str, Any]):
        """Emit a health or lifecycle event to SurrealDB and EventBus."""
        event_dict = {"type": event_type, "data": data, "timestamp": datetime.now().isoformat()}
        try:
            await self.db.create("fleet_events", event_dict)
        except Exception as e:
            logger.error(f"Failed to persist fleet event: {e}")

        try:
            bus = await get_event_bus()
            await bus.publish(
                Event(
                    type=EventType.SYSTEM_HEALTH,
                    source=f"fleet-monitor:{data.get('name', 'unknown')}",
                    payload=event_dict,
                )
            )
        except Exception as e:
            logger.error(f"Failed to publish to EventBus: {e}")

    async def register_service(self, service: ServiceStatus):
        """Register or update a service in the fleet."""
        self.services[service.name] = service
        try:
            await self.db.query(
                "UPSERT fleet_registry CONTENT $service", {"service": service.dict()}
            )
            await self.emit_event(
                "service_registered", {"name": service.name, "port": service.port}
            )
        except Exception as e:
            logger.error(f"Failed to persist service registration: {e}")

    async def spawn_ephemeral_service(self, name: str, port: int, command: list[str]):
        """Spawn a temporary service for testing or offloading."""
        logger.info(f"🚀 Spawning ephemeral service '{name}' on port {port}...")
        try:
            import subprocess

            process = subprocess.Popen(
                command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setpgrp
            )

            service = ServiceStatus(
                name=name,
                port=port,
                type="ephemeral",
                health_url=f"http://localhost:{port}/health",
                pid=process.pid,
                status="starting",
            )
            await self.register_service(service)
            return process.pid
        except Exception as e:
            logger.error(f"Failed to spawn ephemeral service {name}: {e}")
            return None

    async def reap_service(self, name: str):
        """Kill and unregister an ephemeral service."""
        service = self.services.get(name)
        if not service:
            return

        logger.info(f"🧹 Reaping service '{name}'...")
        if service.pid:
            try:
                import signal

                os.killpg(os.getpgid(service.pid), signal.SIGTERM)
            except Exception as e:
                logger.warning(f"Failed to kill service process group: {e}")

        if name in self.services:
            del self.services[name]
        try:
            await self.db.query("DELETE fleet_registry WHERE name = $name", {"name": name})
            await self.emit_event("service_reaped", {"name": name})
        except Exception as e:
            logger.error(f"Failed to delete service from registry: {e}")

    async def check_health(self, name: str):
        """Check health of a specific service."""
        service = self.services.get(name)
        if not service or not service.health_url:
            return

        import httpx

        async with httpx.AsyncClient(timeout=3.0) as client:
            try:
                start_time = time.time()
                response = await client.get(service.health_url)
                latency = time.time() - start_time

                old_status = service.status
                service.status = "healthy" if response.status_code == 200 else "unhealthy"
                service.last_check = datetime.now()
                service.metadata["latency"] = latency

                if old_status != service.status:
                    await self.emit_event(
                        "status_change", {"name": name, "old": old_status, "new": service.status}
                    )

                await self.db.query(
                    "UPDATE fleet_registry CONTENT $service WHERE name = $name",
                    {"service": service.dict(), "name": name},
                )
            except Exception as e:
                if service.status != "down":
                    await self.emit_event("service_down", {"name": name, "error": str(e)})
                    service.status = "down"
                await self.db.query(
                    "UPDATE fleet_registry SET status = 'down' WHERE name = $name", {"name": name}
                )

    async def monitor_loop(self):
        """Continuous polling loop for fleet health."""
        self._running = True
        while self._running:
            for name in list(self.services.keys()):
                await self.check_health(name)
            await asyncio.sleep(60)

    def start(self):
        """Start the background tasks."""
        self._running = True
        if not self._monitor_task:
            self._monitor_task = asyncio.create_task(self.monitor_loop())
        if not self._live_query_task:
            self._live_query_task = asyncio.create_task(self.subscribe_to_events())

    def stop(self):
        """Stop all background tasks."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
        if self._live_query_task:
            self._live_query_task.cancel()


_fleet_monitor: FleetMonitor | None = None


def get_fleet_monitor() -> FleetMonitor:
    global _fleet_monitor
    if _fleet_monitor is None:
        _fleet_monitor = FleetMonitor()
    return _fleet_monitor
