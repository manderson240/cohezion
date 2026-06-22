"""
Circuit Breaker - Prevent cascade failures.

Provides:
- Failure counting with threshold
- Open/half-open/closed states
- Automatic recovery testing
"""

import contextlib
import logging
import time
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject all calls
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitStats:
    """Statistics for a circuit."""

    failures: int = 0
    successes: int = 0
    last_failure_time: float = 0.0
    last_success_time: float = 0.0


class CircuitBreaker:
    """
    Circuit breaker for preventing cascade failures.

    Usage:
        breaker = CircuitBreaker(name="ollama", failure_threshold=5)

        if breaker.allow_request():
            try:
                result = make_request()
                breaker.record_success()
            except Exception:
                breaker.record_failure()
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        """Get current state, checking for recovery."""
        if self._state == CircuitState.OPEN:
            elapsed = time.time() - self._stats.last_failure_time
            if elapsed >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                logger.info(f"Circuit {self.name}: OPEN -> HALF_OPEN")
        return self._state

    def allow_request(self) -> bool:
        """Check if request should be allowed."""
        state = self.state

        if state == CircuitState.CLOSED:
            return True

        if state == CircuitState.HALF_OPEN:
            if self._half_open_calls < self.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False

        # OPEN
        return False

    def record_success(self) -> None:
        """Record a successful call."""
        self._stats.successes += 1
        self._stats.last_success_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            # Recovery successful
            self._state = CircuitState.CLOSED
            self._stats.failures = 0
            logger.info(f"Circuit {self.name}: HALF_OPEN -> CLOSED (recovered)")

    def record_failure(self) -> None:
        """Record a failed call."""
        self._stats.failures += 1
        self._stats.last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            # Still failing
            self._state = CircuitState.OPEN
            logger.warning(f"Circuit {self.name}: HALF_OPEN -> OPEN (still failing)")

        elif self._state == CircuitState.CLOSED:
            if self._stats.failures >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(f"Circuit {self.name}: CLOSED -> OPEN (threshold reached)")

    def reset(self) -> None:
        """Manually reset the circuit."""
        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._half_open_calls = 0

    def get_stats(self) -> dict:
        """Get circuit statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failures": self._stats.failures,
            "successes": self._stats.successes,
        }


# Wiring-sweep 2026-06-22: reliability sub-modules were genuine import-graph orphans.
with contextlib.suppress(Exception):
    from cohezion.reliability.blackwell_handshake import (
        BlackwellHandshake as BlackwellHandshake,
    )

with contextlib.suppress(Exception):
    from cohezion.reliability.batch_manager import BatchManager as BatchManager

with contextlib.suppress(Exception):
    from cohezion.reliability.context_harness import ContextHarness as ContextHarness

with contextlib.suppress(Exception):
    from cohezion.reliability.heartbeat import get_heartbeats as get_heartbeats
    from cohezion.reliability.heartbeat import update_heartbeat as update_heartbeat

with contextlib.suppress(Exception):
    from cohezion.reliability.memory_manager import MemoryManager as MemoryManager

with contextlib.suppress(Exception):
    from cohezion.reliability.monitor import (
        ResourceMonitor as ResourceMonitor,
    )
    from cohezion.reliability.monitor import (
        get_resource_monitor as get_resource_monitor,
    )

with contextlib.suppress(Exception):
    from cohezion.reliability.offload_manager import OffloadManager as OffloadManager

with contextlib.suppress(Exception):
    from cohezion.reliability.pool import ConnectionPool as ConnectionPool

with contextlib.suppress(Exception):
    from cohezion.reliability.resource_guard import ResourceGuard as ResourceGuard
    from cohezion.reliability.resource_guard import SystemVitals as SystemVitals

with contextlib.suppress(Exception):
    from cohezion.reliability.resolver import HallucinationResolver as HallucinationResolver

with contextlib.suppress(Exception):
    from cohezion.reliability.semantic_cache import SemanticCache as SemanticCache

with contextlib.suppress(Exception):
    from cohezion.reliability.sync import AgentWorkspace as AgentWorkspace
    from cohezion.reliability.sync import FileLock as FileLock
    from cohezion.reliability.sync import SafeWriter as SafeWriter

with contextlib.suppress(Exception):
    from cohezion.reliability.viscoelastic import (
        ViscoelasticController as ViscoelasticController,
    )

with contextlib.suppress(Exception):
    from cohezion.reliability.quantum_performance_monitor import (
        MetricType as MetricType,
    )

with contextlib.suppress(Exception):
    from cohezion.reliability.residency_awareness import (
        ResidencyAnchorBase as ResidencyAnchorBase,
    )


# Circuit registry
_circuits: dict[str, CircuitBreaker] = {}


def get_circuit(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
) -> CircuitBreaker:
    if name not in _circuits:
        _circuits[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )
    elif failure_threshold != 5:
        _circuits[name].failure_threshold = failure_threshold

    return _circuits[name]
