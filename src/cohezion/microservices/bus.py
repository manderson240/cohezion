"""High-performance asynchronous microservice event bus with Shannon channel metrics."""

from __future__ import annotations

import asyncio
import math
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from cohezion.microservices.spec import MicroserviceContract


@dataclass
class ShannonEvent:
    """Event envelope governed by information-theoretic transmission invariants."""

    topic: str
    source_service: str
    target_service: str
    payload: dict[str, Any]
    lamport_clock: int = 0
    entropy_bits: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def calculate_entropy(self) -> float:
        """Estimate payload Shannon information entropy in bits."""
        serialized = str(self.payload).encode("utf-8")
        if not serialized:
            return 0.0
        counts: dict[int, int] = {}
        for b in serialized:
            counts[b] = counts.get(b, 0) + 1
        entropy = 0.0
        n = len(serialized)
        for count in counts.values():
            p = count / n
            entropy -= p * math.log2(p)
        self.entropy_bits = round(entropy, 3)
        return self.entropy_bits


EventHandler = Callable[[ShannonEvent], Coroutine[Any, Any, None]]


class ShannonMicroserviceBus:
    """Asynchronous event bus connecting autonomous microservices."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = {}
        self._contracts: dict[str, MicroserviceContract] = {}
        self._global_lamport_clock: int = 0
        self._message_count: int = 0
        self._lock = asyncio.Lock()

    def register_service_contract(self, contract: MicroserviceContract) -> None:
        """Register a microservice contract and bind its declared subscriptions."""
        self._contracts[contract.context.name] = contract

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        """Subscribe an asynchronous handler to an event topic."""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(handler)

    async def publish(self, event: ShannonEvent) -> int:
        """Publish an event to all subscribed microservice handlers."""
        async with self._lock:
            self._global_lamport_clock = max(self._global_lamport_clock, event.lamport_clock) + 1
            event.lamport_clock = self._global_lamport_clock
            self._message_count += 1

        event.calculate_entropy()

        handlers = list(self._subscribers.get(event.topic, []))
        handlers.extend(self._subscribers.get("*", []))

        if handlers:
            tasks = [h(event) for h in handlers]
            await asyncio.gather(*tasks, return_exceptions=True)

        return len(handlers)

    @property
    def total_messages(self) -> int:
        return self._message_count

    @property
    def current_clock(self) -> int:
        return self._global_lamport_clock
