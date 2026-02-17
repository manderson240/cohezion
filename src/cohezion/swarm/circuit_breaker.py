"""Circuit breaker pattern for managing model availability with recovery.

States:
- CLOSED: Normal operation, requests go through
- OPEN: Too many errors, requests rejected
- HALF_OPEN: Testing if model recovered
"""

import logging
import time

from cohezion.swarm.fallback_types import CircuitBreakerState, ModelHealthMetrics


logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker for managing model availability with recovery.

    States:
    - CLOSED: Normal operation, requests go through
    - OPEN: Too many errors, requests rejected
    - HALF_OPEN: Testing if model recovered

    Configuration:
    - error_threshold: Consecutive errors before OPEN (default: 3)
    - recovery_timeout_sec: Seconds before HALF_OPEN test (default: 300s)
    - error_rate_threshold: Error rate threshold for OPEN (default: 50%)
    """

    def __init__(
        self,
        model: str,
        error_threshold: int = 3,
        success_threshold: int = 5,
        recovery_timeout_sec: float = 300.0,
        error_rate_threshold: float = 0.50,
        latency_threshold_ms: float = 5000.0,
    ):
        """Initialize circuit breaker.

        Args:
            model: Model name
            error_threshold: Consecutive errors before OPEN (default: 3)
            success_threshold: Consecutive successes before CLOSED (default: 5)
            recovery_timeout_sec: Seconds before HALF_OPEN test (default: 300s)
            error_rate_threshold: Error rate threshold for OPEN (default: 0.50)
            latency_threshold_ms: Latency threshold for open (default: 5000ms)
        """
        self.model = model
        self.error_threshold = error_threshold
        self.success_threshold = success_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        self.error_rate_threshold = error_rate_threshold
        self.latency_threshold_ms = latency_threshold_ms

        self.state = CircuitBreakerState.CLOSED
        self.metrics = ModelHealthMetrics(model=model)
        self.opened_at: float | None = None

    def record_success(self, latency_ms: float = 0.0) -> None:
        """Record successful execution.

        Args:
            latency_ms: Response latency in milliseconds
        """
        self.metrics.error_count = 0
        self.metrics.success_count += 1
        self.metrics.last_success_time = time.time()
        self.metrics.total_requests += 1
        self.metrics.last_latency_ms = latency_ms

        if self.metrics.avg_latency_ms == 0.0:
            self.metrics.avg_latency_ms = latency_ms
        else:
            self.metrics.avg_latency_ms = (
                0.7 * self.metrics.avg_latency_ms + 0.3 * latency_ms
            )

        if (
            self.state == CircuitBreakerState.HALF_OPEN
            and self.metrics.success_count >= self.success_threshold
        ):
            self._transition_to_closed()

    def record_error(self, latency_ms: float = 0.0) -> None:
        """Record failed execution.

        Args:
            latency_ms: Latency before failure (for tracking slow failures)
        """
        self.metrics.error_count += 1
        self.metrics.success_count = 0
        self.metrics.last_error_time = time.time()
        self.metrics.total_requests += 1
        self.metrics.total_errors += 1
        self.metrics.last_latency_ms = latency_ms

        if self.metrics.error_count >= self.error_threshold:
            logger.warning(
                "Circuit breaker: %s - %d consecutive errors threshold reached",
                self.model,
                self.metrics.error_count,
            )
            self._transition_to_open()

        if (
            self.metrics.total_requests >= 10
            and self.metrics.error_rate >= self.error_rate_threshold
        ):
            logger.warning(
                "Circuit breaker: %s - error rate %.1f%% exceeds threshold",
                self.model,
                self.metrics.error_rate * 100,
            )
            self._transition_to_open()

    def record_latency_spike(self) -> None:
        """Record latency spike (slow response detected)."""
        if self.metrics.last_latency_ms > self.latency_threshold_ms:
            logger.warning(
                "Circuit breaker: %s - latency spike %.0fms exceeds threshold",
                self.model,
                self.metrics.last_latency_ms,
            )

    def allow_request(self) -> bool:
        """Check if request should be allowed.

        Returns:
            True if request allowed, False if circuit is open
        """
        if self.state == CircuitBreakerState.CLOSED:
            return True

        if self.state == CircuitBreakerState.OPEN:
            if self.opened_at:
                elapsed = time.time() - self.opened_at
                if elapsed >= self.recovery_timeout_sec:
                    self._transition_to_half_open()
                    return True
            return False

        return self.state == CircuitBreakerState.HALF_OPEN

    def _transition_to_open(self) -> None:
        """Transition to OPEN state."""
        if self.state != CircuitBreakerState.OPEN:
            logger.warning(
                "Circuit breaker OPEN for %s: error_count=%d, error_rate=%.1f%%",
                self.model,
                self.metrics.error_count,
                self.metrics.error_rate * 100,
            )
            self.state = CircuitBreakerState.OPEN
            self.opened_at = time.time()

    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state (testing recovery)."""
        if self.state != CircuitBreakerState.HALF_OPEN:
            logger.info(
                "Circuit breaker HALF_OPEN for %s: testing recovery after %.0fs",
                self.model,
                self.recovery_timeout_sec,
            )
            self.state = CircuitBreakerState.HALF_OPEN
            self.metrics.error_count = 0
            self.metrics.success_count = 0

    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state (recovered)."""
        if self.state != CircuitBreakerState.CLOSED:
            downtime_sec = time.time() - (self.opened_at or 0)
            logger.info(
                "Circuit breaker CLOSED for %s: recovered after %.1fs downtime",
                self.model,
                downtime_sec,
            )
            self.state = CircuitBreakerState.CLOSED
            self.opened_at = None
            self.metrics.error_count = 0
            self.metrics.success_count = 0

    def reset(self) -> None:
        """Reset circuit breaker (testing only)."""
        self.state = CircuitBreakerState.CLOSED
        self.opened_at = None
        self.metrics = ModelHealthMetrics(model=self.model)
