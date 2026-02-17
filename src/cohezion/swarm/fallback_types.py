"""Shared types for fallback strategy."""

import time
from dataclasses import dataclass, field
from enum import Enum


class CircuitBreakerState(Enum):
    """Circuit breaker states for model availability."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ModelHealthMetrics:
    """Health metrics tracking for a model."""

    model: str
    error_count: int = 0
    success_count: int = 0
    last_error_time: float | None = field(default=None)
    last_success_time: float | None = field(default=None)
    total_requests: int = 0
    total_errors: int = 0
    avg_latency_ms: float = 0.0
    last_latency_ms: float = 0.0

    @property
    def error_rate(self) -> float:
        """Calculate error rate (0.0-1.0)."""
        if self.total_requests == 0:
            return 0.0
        return self.total_errors / self.total_requests

    @property
    def health_score(self) -> float:
        """Calculate overall health score (0.0-1.0).

        High score = healthy model, low score = unhealthy.
        Based on: error rate, stability, recency of errors.
        """
        health = 1.0 - self.error_rate

        if self.success_count >= 5:
            health = min(1.0, health + 0.1)

        if self.last_error_time:
            seconds_since_error = time.time() - self.last_error_time
            if seconds_since_error < 300:
                health *= 0.8
            elif seconds_since_error < 600:
                health *= 0.9

        return max(0.0, min(1.0, health))


@dataclass
class FallbackEvent:
    """Record of a fallback occurrence."""

    timestamp: float
    primary_model: str
    fallback_model: str
    reason: str
    cost_saved_usd: float = 0.0
    quality_loss: float = 0.0
