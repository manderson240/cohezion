"""Event-driven architecture for decoupled communication.

Replaces direct coupling between agents and logging/monitoring systems.
Pattern: Pub/Sub with typed events and async handlers.
"""

from __future__ import annotations

import asyncio
import contextlib
import itertools
import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Protocol


logger = logging.getLogger(__name__)


class EventType(Enum):
    """Standard event types across the system."""

    AGENT_START = auto()
    AGENT_COMPLETE = auto()
    AGENT_ERROR = auto()
    LLM_CALL = auto()
    LLM_RESPONSE = auto()
    CACHE_HIT = auto()
    CACHE_MISS = auto()
    DB_QUERY = auto()
    DB_ERROR = auto()
    SECURITY_VIOLATION = auto()
    METRIC_UPDATE = auto()
    SYSTEM_HEALTH = auto()
    JOURNEY_STEP = auto()
    CUSTOM = auto()

    # DataMesh domain events (DataMeshEventBridge, CorpusQualityConsumer)
    DATA_PRODUCT_CREATED = auto()
    DATA_PRODUCT_UPDATED = auto()
    DATA_PRODUCT_QUALITY_ALERT = auto()
    LINEAGE_UPDATED = auto()
    DOMAIN_HEALTH_DEGRADED = auto()


@dataclass(frozen=True, slots=True)
class Event:
    """Immutable event with metadata."""

    type: EventType
    source: str
    timestamp: float = field(default_factory=time.time)
    payload: dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Higher = processed first

    @classmethod
    def agent_start(cls, agent_name: str, model: str, **kwargs) -> Event:
        return cls(
            type=EventType.AGENT_START,
            source=agent_name,
            payload={"model": model, **kwargs},
        )

    @classmethod
    def agent_complete(cls, agent_name: str, result: Any, duration_ms: float, **kwargs) -> Event:
        return cls(
            type=EventType.AGENT_COMPLETE,
            source=agent_name,
            payload={"result": result, "duration_ms": duration_ms, **kwargs},
        )

    @classmethod
    def llm_call(cls, agent_name: str, model: str, prompt_tokens: int = 0, **kwargs) -> Event:
        return cls(
            type=EventType.LLM_CALL,
            source=agent_name,
            payload={"model": model, "prompt_tokens": prompt_tokens, **kwargs},
        )

    @classmethod
    def cache_access(cls, agent_name: str, hit: bool, tier: str | None = None, **kwargs) -> Event:
        return cls(
            type=EventType.CACHE_HIT if hit else EventType.CACHE_MISS,
            source=agent_name,
            payload={"tier": tier, **kwargs},
        )


EventHandler = Callable[[Event], Awaitable[None]]


class EventHandlerProtocol(Protocol):
    """Protocol for event handlers."""

    async def handle(self, event: Event) -> None: ...


class EventBus:
    """Central event bus for decoupled communication.

    Usage:
        bus = EventBus()

        # Subscribe
        @bus.subscribe(EventType.LLM_CALL)
        async def log_llm_call(event: Event):
            logger.info(f"LLM call from {event.source}")

        # Publish
        await bus.publish(Event.llm_call("MyAgent", "gpt-4"))
    """

    def __init__(self, max_queue_size: int = 10000):
        self._handlers: dict[EventType, list[EventHandler]] = defaultdict(list)
        self._wildcard_handlers: list[EventHandler] = []
        self._queue: asyncio.PriorityQueue[tuple[int, int, Event]] = asyncio.PriorityQueue(
            maxsize=max_queue_size
        )
        self._seq = itertools.count()  # monotonic tie-breaker — prevents Event.__lt__ comparison
        self._processor_task: asyncio.Task | None = None
        self._running = False
        self._metrics = {
            "published": 0,
            "delivered": 0,
            "dropped": 0,
            "errors": 0,
        }

    async def start(self) -> None:
        """Start the event processor."""
        if not self._running:
            self._running = True
            self._processor_task = asyncio.create_task(self._process_loop())
            logger.info("EventBus started")

    async def stop(self) -> None:
        """Stop the event processor."""
        self._running = False
        if self._processor_task:
            # Wait for queue to drain
            await self._queue.join()
            self._processor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._processor_task
        logger.info(f"EventBus stopped. Metrics: {self._metrics}")

    def subscribe(
        self, event_type: EventType | None = None
    ) -> Callable[[EventHandler], EventHandler]:
        """Decorator to subscribe to events.

        @bus.subscribe(EventType.LLM_CALL)
        async def handler(event): ...

        @bus.subscribe()  # Wildcard - all events
        async def log_all(event): ...
        """

        def decorator(handler: EventHandler) -> EventHandler:
            if event_type is None:
                self._wildcard_handlers.append(handler)
            else:
                self._handlers[event_type].append(handler)
            return handler

        return decorator

    def unsubscribe(self, handler: EventHandler, event_type: EventType | None = None) -> None:
        """Remove a handler subscription."""
        if event_type is None:
            if handler in self._wildcard_handlers:
                self._wildcard_handlers.remove(handler)
        else:
            if handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)

    async def publish(self, event: Event) -> bool:
        """Publish event to all subscribers."""
        try:
            # Priority queue: (-priority, seq, event) — seq prevents Event comparison on tie
            await self._queue.put((-event.priority, next(self._seq), event))
            self._metrics["published"] += 1
            return True
        except asyncio.QueueFull:
            self._metrics["dropped"] += 1
            logger.warning(f"Event dropped (queue full): {event.type}")
            return False

    async def _process_loop(self) -> None:
        """Main processing loop."""
        while self._running:
            try:
                _, _, event = await self._queue.get()
                await self._dispatch(event)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Event processing error: {e}")
                self._metrics["errors"] += 1

    async def _dispatch(self, event: Event) -> None:
        """Dispatch event to all relevant handlers."""
        handlers = []

        # Type-specific handlers
        if event.type in self._handlers:
            handlers.extend(self._handlers[event.type])

        # Wildcard handlers
        handlers.extend(self._wildcard_handlers)

        if not handlers:
            return

        # Execute all handlers concurrently
        results = await asyncio.gather(
            *[self._safe_handle(h, event) for h in handlers], return_exceptions=True
        )

        delivered = sum(1 for r in results if r is None)
        self._metrics["delivered"] += delivered

    async def _safe_handle(self, handler: EventHandler, event: Event) -> None:
        """Execute handler with error isolation."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Handler error for {event.type}: {e}")
            self._metrics["errors"] += 1

    def get_metrics(self) -> dict[str, Any]:
        """Get bus metrics."""
        return {
            **self._metrics,
            "queue_size": self._queue.qsize(),
            "handlers": {t.name: len(h) for t, h in self._handlers.items()},
            "wildcard_handlers": len(self._wildcard_handlers),
        }


class EventFilter(ABC):
    """Base class for event filtering middleware."""

    @abstractmethod
    async def filter(self, event: Event) -> Event | None:
        """Filter/transform event. Return None to drop."""
        pass


class SamplingFilter(EventFilter):
    """Sample events at a given rate."""

    def __init__(self, sample_rate: float = 0.1):
        self.sample_rate = sample_rate
        self._counter = 0

    async def filter(self, event: Event) -> Event | None:
        self._counter += 1
        if self._counter % int(1 / self.sample_rate) == 0:
            return event
        return None


class RoutingFilter(EventFilter):
    """Route events based on predicates."""

    def __init__(self):
        self._routes: list[tuple[Callable[[Event], bool], EventBus]] = []

    def route(self, predicate: Callable[[Event], bool], bus: EventBus) -> None:
        """Add a route."""
        self._routes.append((predicate, bus))

    async def filter(self, event: Event) -> Event | None:
        """Route event to matching buses."""
        for predicate, bus in self._routes:
            if predicate(event):
                await bus.publish(event)
        return event


# Global event bus singleton
_event_bus: EventBus | None = None


async def get_event_bus() -> EventBus:
    """Get or create global event bus."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
        await _event_bus.start()
    return _event_bus


def reset_event_bus() -> None:
    """Reset global event bus (for testing)."""
    global _event_bus
    _event_bus = None


class EventHandlerGroup:
    """Group of handlers that can be managed together."""

    def __init__(self, bus: EventBus):
        self._bus = bus
        self._handlers: list[tuple[EventType | None, EventHandler]] = []

    def add(self, event_type: EventType | None, handler: EventHandler) -> None:
        """Add handler to group."""
        self._handlers.append((event_type, handler))

    async def subscribe_all(self) -> None:
        """Subscribe all handlers."""
        for event_type, handler in self._handlers:
            if event_type is None:
                self._bus._wildcard_handlers.append(handler)
            else:
                self._bus._handlers[event_type].append(handler)

    async def unsubscribe_all(self) -> None:
        """Unsubscribe all handlers."""
        for event_type, handler in self._handlers:
            self._bus.unsubscribe(handler, event_type)
