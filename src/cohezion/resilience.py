"""
ASCENDED COHEZION - Resilience & Retry Patterns
Compound Engineering Layer 3: Operational Resilience

Provides retry logic, circuit breakers, and fallback strategies.
Builds on Layers 1-2 to enable 24/7 autonomous operation.
"""

import asyncio
import functools
import logging
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""

    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_exceptions: tuple = (Exception,)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascade failures.

    Compound Engineering: Once circuit breaker is in place,
    we can safely add more external calls without worrying about
    cascade failures.
    """

    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.half_open_calls = 0
        self._lock = asyncio.Lock()

        logger.info(f"⚡ CircuitBreaker initialized: {name}")

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection"""
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time >= self.config.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    logger.info(f"⚡ Circuit {self.name} entering HALF_OPEN state")
                else:
                    raise CircuitBreakerOpen(f"Circuit {self.name} is OPEN")

            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitBreakerOpen(
                        f"Circuit {self.name} HALF_OPEN limit reached"
                    )
                self.half_open_calls += 1

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            await self._on_success()
            return result

        except Exception as e:
            await self._on_failure()
            raise

    async def _on_success(self):
        """Handle successful call"""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.half_open_max_calls:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    logger.info(f"⚡ Circuit {self.name} CLOSED (recovered)")
            else:
                self.failure_count = max(0, self.failure_count - 1)

    async def _on_failure(self):
        """Handle failed call"""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                logger.warning(f"⚡ Circuit {self.name} OPENED (recovery failed)")
            elif self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(
                    f"⚡ Circuit {self.name} OPENED ({self.failure_count} failures)"
                )

    @property
    def is_healthy(self) -> bool:
        """Check if circuit is healthy"""
        return self.state == CircuitState.CLOSED


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open"""

    pass


class ResilientOperation:
    """
    Combines retry logic with circuit breaker for resilient operations.

    This is the main interface for resilient operations - it wraps
    any function with retry logic and circuit breaker protection.
    """

    def __init__(
        self,
        name: str,
        retry_config: RetryConfig = None,
        circuit_config: CircuitBreakerConfig = None,
    ):
        self.name = name
        self.retry_config = retry_config or RetryConfig()
        self.circuit = CircuitBreaker(name, circuit_config)

    async def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute with retry and circuit breaker"""
        last_exception = None
        delay = self.retry_config.initial_delay

        for attempt in range(1, self.retry_config.max_attempts + 1):
            try:
                # Try through circuit breaker
                return await self.circuit.call(func, *args, **kwargs)

            except CircuitBreakerOpen:
                # Circuit is open, wait and retry
                logger.warning(
                    f"🔁 {self.name}: Circuit open, waiting {delay}s (attempt {attempt})"
                )
                await asyncio.sleep(delay)
                delay = min(
                    delay * self.retry_config.exponential_base,
                    self.retry_config.max_delay,
                )
                if self.retry_config.jitter:
                    delay *= 0.5 + random.random()

            except self.retry_config.retry_exceptions as e:
                last_exception = e
                if attempt < self.retry_config.max_attempts:
                    logger.warning(
                        f"🔁 {self.name}: Attempt {attempt} failed, retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                    delay = min(
                        delay * self.retry_config.exponential_base,
                        self.retry_config.max_delay,
                    )
                    if self.retry_config.jitter:
                        delay *= 0.5 + random.random()
                else:
                    logger.error(
                        f"❌ {self.name}: All {self.retry_config.max_attempts} attempts failed"
                    )
                    raise last_exception

        raise last_exception or Exception(f"Operation {self.name} failed")


def resilient(
    name: str,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    circuit_threshold: int = 5,
):
    """
    Decorator to make any function resilient.

    Usage:
        @resilient(name="model_call", max_attempts=3)
        async def call_model(prompt):
            return await model.generate(prompt)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        retry_config = RetryConfig(
            max_attempts=max_attempts, initial_delay=initial_delay
        )
        circuit_config = CircuitBreakerConfig(failure_threshold=circuit_threshold)
        resilient_op = ResilientOperation(name, retry_config, circuit_config)

        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await resilient_op.execute(func, *args, **kwargs)

        wrapper._resilient_op = resilient_op
        return wrapper

    return decorator


class Bulkhead:
    """
    Bulkhead pattern to isolate failures.

    Limits concurrent operations to prevent resource exhaustion.
    """

    def __init__(self, name: str, max_concurrent: int = 10, max_queue: int = 100):
        self.name = name
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.queue_size = asyncio.Semaphore(max_queue)
        self.metrics = {"active": 0, "queued": 0, "completed": 0, "rejected": 0}

        logger.info(
            f"🚢 Bulkhead {name}: max_concurrent={max_concurrent}, max_queue={max_queue}"
        )

    async def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute with bulkhead protection"""
        if not self.queue_size.acquire(blocking=False):
            self.metrics["rejected"] += 1
            raise BulkheadFull(f"Bulkhead {self.name} queue full")

        try:
            self.metrics["queued"] += 1
            async with self.semaphore:
                self.metrics["active"] += 1
                self.metrics["queued"] -= 1

                try:
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)
                    self.metrics["completed"] += 1
                    return result
                finally:
                    self.metrics["active"] -= 1
        finally:
            self.queue_size.release()

    def get_metrics(self) -> dict:
        """Get current bulkhead metrics"""
        return self.metrics.copy()


class BulkheadFull(Exception):
    """Exception raised when bulkhead is full"""

    pass


class Timeout:
    """Timeout wrapper for operations"""

    def __init__(self, seconds: float):
        self.seconds = seconds

    async def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute with timeout"""
        return await asyncio.wait_for(
            func(*args, **kwargs)
            if asyncio.iscoroutinefunction(func)
            else asyncio.to_thread(func, *args, **kwargs),
            timeout=self.seconds,
        )


# Pre-configured resilient operations for common use cases


class ResilientCloudCall(ResilientOperation):
    """Resilient operation for cloud model calls"""

    def __init__(self, name: str = "cloud_call"):
        super().__init__(
            name=name,
            retry_config=RetryConfig(
                max_attempts=5,
                initial_delay=2.0,
                max_delay=30.0,
                retry_exceptions=(Exception,),
            ),
            circuit_config=CircuitBreakerConfig(
                failure_threshold=3, recovery_timeout=30.0
            ),
        )


class ResilientDBCall(ResilientOperation):
    """Resilient operation for database calls"""

    def __init__(self, name: str = "db_call"):
        super().__init__(
            name=name,
            retry_config=RetryConfig(
                max_attempts=3,
                initial_delay=0.5,
                max_delay=10.0,
                retry_exceptions=(Exception,),
            ),
            circuit_config=CircuitBreakerConfig(
                failure_threshold=10, recovery_timeout=5.0
            ),
        )


class ResilientMission(ResilientOperation):
    """Resilient operation for mission-critical operations"""

    def __init__(self, name: str = "mission_op"):
        super().__init__(
            name=name,
            retry_config=RetryConfig(
                max_attempts=10,
                initial_delay=5.0,
                max_delay=300.0,
                retry_exceptions=(Exception,),
            ),
            circuit_config=CircuitBreakerConfig(
                failure_threshold=20, recovery_timeout=60.0
            ),
        )


# Global resilient operations
_cloud_call = None
_db_call = None
_mission_op = None


async def get_resilient_cloud_call() -> ResilientCloudCall:
    """Get global resilient cloud call handler"""
    global _cloud_call
    if _cloud_call is None:
        _cloud_call = ResilientCloudCall()
    return _cloud_call


async def get_resilient_db_call() -> ResilientDBCall:
    """Get global resilient DB call handler"""
    global _db_call
    if _db_call is None:
        _db_call = ResilientDBCall()
    return _db_call


async def get_resilient_mission() -> ResilientMission:
    """Get global resilient mission handler"""
    global _mission_op
    if _mission_op is None:
        _mission_op = ResilientMission()
    return _mission_op
