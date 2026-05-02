"""
Telemetry Bus: Non-blocking event distribution for Cohezion telemetry.
Decouples high-frequency 12D trajectory capture from core orchestration.
Integrates with Cohezion reliability circuits.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from cohezion.data_mesh.journey_telemetry import FlumeJourneyEvent


logger = logging.getLogger(__name__)


class TelemetryBus:
    """
    Asynchronous event bus for telemetry.
    Uses an internal queue to ensure zero-latency for the producer.
    """

    def __init__(self, queue_size: int = 1000):
        self._queue: asyncio.Queue[FlumeJourneyEvent] = asyncio.Queue(maxsize=queue_size)
        self._subscribers: list[Callable[[FlumeJourneyEvent], Any]] = []
        self._worker_task: asyncio.Task | None = None
        self._running = False

    async def start(self):
        """Start the background consumer worker."""
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("📡 Telemetry Bus started (Worker active)")

    async def stop(self):
        """Stop the background worker and wait for queue drain."""
        self._running = False
        if self._worker_task:
            # We don't wait for drain here for speed, but could implement it.
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("📡 Telemetry Bus stopped")

    async def emit(self, event: FlumeJourneyEvent):
        """
        Emit a telemetry event. Non-blocking (fast-fail if queue full).
        """
        print(f"[DEBUG] TelemetryBus: Emitting event {event.event_id}")
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("⚠️ Telemetry Bus queue full! Dropping event: %s", event.event_id)

    async def _worker_loop(self):
        """Background loop to distribute events to subscribers."""
        while self._running:
            try:
                event = await self._queue.get()
                print(
                    f"[DEBUG] TelemetryBus: Processing event {event.event_id} for {len(self._subscribers)} subscribers"
                )

                # Distribute to subscribers (e.g., SurrealDB, Ouroboros)
                for subscriber in self._subscribers:
                    try:
                        # Subscribers should ideally be non-blocking or wrapped in a circuit
                        if asyncio.iscoroutinefunction(subscriber):
                            await subscriber(event)
                        else:
                            subscriber(event)
                    except Exception as e:
                        logger.error("❌ Telemetry Bus subscriber error: %s", e)

                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("❌ Telemetry Bus worker error: %s", e)
                await asyncio.sleep(0.1)

    def subscribe(self, callback: Callable[[FlumeJourneyEvent], Any]):
        """Register a callback for telemetry events."""
        self._subscribers.append(callback)


# Singleton
_BUS = None


def get_telemetry_bus() -> TelemetryBus:
    global _BUS
    if _BUS is None:
        _BUS = TelemetryBus()
    return _BUS
