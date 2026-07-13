"""Circuit breaker for protecting against cascading failures.

Provides a decorator-based circuit breaker pattern. When a function fails
`failure_threshold` times consecutively, the circuit opens and subsequent
calls fail-fast until `recovery_timeout` seconds have elapsed.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TypeVar


logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class Circuit:
    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time > self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def record_success(self) -> None:
        self._failure_count = 0
        if self._state in (CircuitState.OPEN, CircuitState.HALF_OPEN):
            self._state = CircuitState.CLOSED
            logger.info("Circuit %s closed (recovered)", self.name)

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning("Circuit %s opened after %d failures", self.name, self._failure_count)

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        if self.state == CircuitState.OPEN:
            raise CircuitOpenError(f"Circuit {self.name} is open")
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise


class CircuitOpenError(Exception):
    pass


_circuits: dict[str, Circuit] = {}


def get_circuit(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
) -> Callable[[F], F]:
    """Decorator factory: wrap an async function with a named circuit breaker.

    Usage::

        @get_circuit(name="moe_routing", failure_threshold=3, recovery_timeout=30)
        async def route_task(req):
            ...
    """
    if name not in _circuits:
        _circuits[name] = Circuit(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )
    circuit = _circuits[name]

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await circuit.call(func, *args, **kwargs)

        wrapper.circuit = circuit  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator
