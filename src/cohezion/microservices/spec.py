"""Formal specifications and contracts for autonomous microservices."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class MicroserviceStatus(StrEnum):
    """Lifecycle and operational status of an autonomous microservice."""

    STARTING = "STARTING"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    HEALING = "HEALING"
    STOPPED = "STOPPED"


@dataclass(frozen=True)
class BoundedContext:
    """Domain-Driven Bounded Context definition architected by a digital twin."""

    name: str
    lead_scientist: str
    scientific_domain: str
    description: str
    consolidated_modules: list[str]
    invariants: list[str] = field(default_factory=list)


@dataclass
class MicroserviceHealth:
    """Real-time telemetry and health diagnostics."""

    service_name: str
    status: MicroserviceStatus
    latency_ms: float
    memory_mb: float
    error_rate: float
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def is_operational(self) -> bool:
        return self.status in {MicroserviceStatus.HEALTHY, MicroserviceStatus.HEALING}


@dataclass
class MicroserviceContract:
    """Decoupled interface contract governing an autonomous microservice."""

    context: BoundedContext
    port: int
    published_events: list[str]
    subscribed_events: list[str]
    max_latency_ms: float = 100.0
    zero_copy_ipc: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate_event_compatibility(self, event_name: str) -> bool:
        """Verify whether an incoming event name is registered in subscriptions."""
        return event_name in self.subscribed_events or "*" in self.subscribed_events
