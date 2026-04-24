# ruff: noqa: RUF012  # class attrs treated as immutable config; never mutated per-instance
"""Intelligent model fallback strategy with circuit breaker pattern.

Features:
- Fallback chain: preferred → secondary → emergency
- Circuit breaker for unavailable/degraded models
- Adaptive fallback based on cost and quality
- Auto-recovery after configurable time window
- Preserve cost savings during fallback

Architecture:
  Model Selection
       ↓
  Is primary available? (circuit breaker check)
       ↓
       YES: Use it
       NO: Try secondary
       ↓
  Is secondary available?
       ↓
       YES: Use it
       NO: Try emergency (deepseek)
       ↓
  Record degradation → Learn for next time
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Model unavailable, reject requests
    HALF_OPEN = "half_open"  # Testing if model recovered


@dataclass
class ModelHealthMetrics:
    """Health metrics for a model."""

    model: str
    error_count: int = 0  # Consecutive errors
    success_count: int = 0  # Consecutive successes
    last_error_time: float | None = field(default=None)
    last_success_time: float | None = field(default=None)
    total_requests: int = 0
    total_errors: int = 0
    avg_latency_ms: float = 0.0

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
        """
        # Base on error rate (1.0 - error_rate)
        health = 1.0 - self.error_rate

        # Adjust for consecutive successes (stability)
        if self.success_count >= 5:
            health = min(1.0, health + 0.1)

        # Degrade for recent errors
        if self.last_error_time:
            seconds_since_error = time.time() - self.last_error_time
            if seconds_since_error < 300:  # Recent error (<5 min)
                health *= 0.8

        return max(0.0, min(1.0, health))


class ModelCircuitBreaker:
    """Circuit breaker for managing model availability.

    States:
    - CLOSED: Normal operation, requests go through
    - OPEN: Too many errors, requests rejected
    - HALF_OPEN: Testing if model recovered

    Thresholds:
    - Error threshold: 3 consecutive errors → OPEN
    - Recovery threshold: 5 consecutive successes → CLOSED
    - Recovery timeout: 5 minutes before half-open test
    """

    def __init__(
        self,
        model: str,
        error_threshold: int = 3,
        success_threshold: int = 5,
        recovery_timeout_sec: float = 300.0,  # 5 minutes
        error_rate_threshold: float = 0.50,  # 50% error rate
    ):
        """Initialize circuit breaker.

        Args:
            model: Model name
            error_threshold: Consecutive errors before OPEN (default: 3)
            success_threshold: Consecutive successes before CLOSED (default: 5)
            recovery_timeout_sec: Seconds before HALF_OPEN test (default: 300s)
            error_rate_threshold: Error rate threshold for OPEN (default: 0.50)
        """
        self.model = model
        self.error_threshold = error_threshold
        self.success_threshold = success_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        self.error_rate_threshold = error_rate_threshold

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

        # Update average latency (exponential moving average)
        if self.metrics.avg_latency_ms == 0.0:
            self.metrics.avg_latency_ms = latency_ms
        else:
            self.metrics.avg_latency_ms = 0.7 * self.metrics.avg_latency_ms + 0.3 * latency_ms

        # If HALF_OPEN and succeeded, go back to CLOSED
        if self.state == CircuitBreakerState.HALF_OPEN:
            if self.metrics.success_count >= self.success_threshold:
                self._transition_to_closed()

    def record_error(self) -> None:
        """Record failed execution."""
        self.metrics.error_count += 1
        self.metrics.success_count = 0
        self.metrics.last_error_time = time.time()
        self.metrics.total_requests += 1
        self.metrics.total_errors += 1

        # If too many consecutive errors, open circuit
        if self.metrics.error_count >= self.error_threshold:
            self._transition_to_open()

        # If error rate too high (only check after enough samples)
        if (
            self.metrics.total_requests >= 10
            and self.metrics.error_rate >= self.error_rate_threshold
        ):
            self._transition_to_open()

    def allow_request(self) -> bool:
        """Check if request should be allowed.

        Returns:
            True if request allowed, False if circuit is open
        """
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout expired
            if self.opened_at:
                elapsed = time.time() - self.opened_at
                if elapsed >= self.recovery_timeout_sec:
                    # Try recovery
                    self._transition_to_half_open()
                    return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            # Allow one test request
            return True
        else:
            return False

    def _transition_to_open(self) -> None:
        """Transition to OPEN state."""
        if self.state != CircuitBreakerState.OPEN:
            logger.warning(
                f"Circuit breaker OPEN for {self.model}: "
                f"error_count={self.metrics.error_count}, "
                f"error_rate={self.metrics.error_rate:.2%}"
            )
            self.state = CircuitBreakerState.OPEN
            self.opened_at = time.time()

    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state (testing recovery)."""
        if self.state != CircuitBreakerState.HALF_OPEN:
            logger.info(
                f"Circuit breaker HALF_OPEN for {self.model}: "
                f"testing recovery after {self.recovery_timeout_sec}s"
            )
            self.state = CircuitBreakerState.HALF_OPEN
            self.metrics.error_count = 0
            self.metrics.success_count = 0

    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state (recovered)."""
        if self.state != CircuitBreakerState.CLOSED:
            logger.info(
                f"Circuit breaker CLOSED for {self.model}: recovered "
                f"after {time.time() - (self.opened_at or 0):.1f}s downtime"
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


class ModelFallbackStrategy:
    """Intelligent fallback strategy with circuit breakers.

    Manages fallback chain:
    1. Primary model (selected by cost-aware router)
    2. Secondary model (alternative suggestion)
    3. Emergency model (always available, high quality)

    Features:
    - Circuit breaker per model (mark unavailable, auto-recovery)
    - Cost-aware fallback (choose next cheapest available)
    - Quality preservation (ensure fallback quality acceptable)
    - Graceful degradation (continue service during outages)
    - Recovery tracking (learn from past degradations)
    """

    # Model fallback chains (primary → secondary → emergency)
    DEFAULT_FALLBACK_CHAINS = {
        "phi3:mini": ["qwen3-coder:32b", "deepseek-r1:8b"],
        "qwen3-coder:32b": ["phi3:mini", "deepseek-r1:8b"],
        "deepseek-r1:8b": ["qwen3-coder:32b", "phi3:mini"],
        "gemma3:4b": ["phi3:mini", "deepseek-r1:8b"],
        "mistral:7b": ["qwen3-coder:32b", "deepseek-r1:8b"],
        "llama4-scout": ["phi3:mini", "deepseek-r1:8b"],
    }

    # Model quality scores (0.0-1.0)
    MODEL_QUALITY = {
        "phi3:mini": 0.6,
        "qwen3-coder:32b": 0.82,
        "deepseek-r1:8b": 0.95,
        "gemma3:4b": 0.55,
        "mistral:7b": 0.75,
        "llama4-scout": 0.70,
    }

    def __init__(
        self,
        error_threshold: int = 3,
        recovery_timeout_sec: float = 300.0,
        min_quality_loss: float = 0.10,  # Max 10% quality loss in fallback
    ):
        """Initialize fallback strategy.

        Args:
            error_threshold: Consecutive errors before marking unavailable
            recovery_timeout_sec: Seconds before retrying unavailable model
            min_quality_loss: Max acceptable quality loss in fallback (0.0-1.0)
        """
        self.error_threshold = error_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        self.min_quality_loss = min_quality_loss

        # Circuit breakers per model
        self.circuit_breakers: dict[str, ModelCircuitBreaker] = {}

        # Degradation tracking
        self.fallback_count: int = 0
        self.fallback_history: list[tuple[str, str, float]] = []  # (primary, fallback, time)

    def select_model(
        self,
        primary_model: str,
        available_models: list[str],
        quality_scores: dict[str, float] | None = None,
    ) -> tuple[str, bool]:
        """Select model with fallback support.

        Args:
            primary_model: Primary model choice
            available_models: All available models
            quality_scores: Optional quality scores per model

        Returns:
            (selected_model, is_degraded)
            - selected_model: Model to use
            - is_degraded: True if fallback used
        """
        quality_scores = quality_scores or self.MODEL_QUALITY

        # Check if primary available
        primary_breaker = self._get_breaker(primary_model)
        if primary_breaker.allow_request():
            return primary_model, False

        # Try fallback chain
        fallback_chain = self.DEFAULT_FALLBACK_CHAINS.get(primary_model, available_models)

        for fallback_model in fallback_chain:
            if fallback_model not in available_models:
                continue

            fallback_breaker = self._get_breaker(fallback_model)
            if not fallback_breaker.allow_request():
                continue

            # Check quality loss acceptable
            primary_quality = quality_scores.get(primary_model, 0.7)
            fallback_quality = quality_scores.get(fallback_model, 0.7)
            quality_loss = (primary_quality - fallback_quality) / max(primary_quality, 0.01)

            if quality_loss <= self.min_quality_loss:
                # Use fallback
                self._record_fallback(primary_model, fallback_model)
                return fallback_model, True

        # No acceptable fallback, try emergency (deepseek if available and not primary)
        if primary_model != "deepseek-r1:8b" and "deepseek-r1:8b" in available_models:
            logger.warning(
                f"Using emergency fallback: {primary_model} unavailable, "
                f"using deepseek-r1:8b (quality loss unacceptable)"
            )
            self._record_fallback(primary_model, "deepseek-r1:8b")
            return "deepseek-r1:8b", True

        # Last resort: use any available model that's not the primary
        available_non_primary = [m for m in available_models if m != primary_model]
        if available_non_primary:
            selected = available_non_primary[0]
            logger.error(f"All models degraded or primary unavailable, using fallback: {selected}")
            self._record_fallback(primary_model, selected)
            return selected, True

        # Absolute last resort: return primary anyway
        logger.error(f"No alternative models available, forced to use primary: {primary_model}")
        return primary_model, True

    def record_execution(self, model: str, success: bool, latency_ms: float = 0.0) -> None:
        """Record execution result for circuit breaker.

        Args:
            model: Model used
            success: Whether execution succeeded
            latency_ms: Response latency in milliseconds
        """
        breaker = self._get_breaker(model)

        if success:
            breaker.record_success(latency_ms)
        else:
            breaker.record_error()

    def get_model_health(self, model: str) -> ModelHealthMetrics:
        """Get health metrics for a model.

        Args:
            model: Model name

        Returns:
            ModelHealthMetrics
        """
        return self._get_breaker(model).metrics

    def get_all_health(self) -> dict[str, ModelHealthMetrics]:
        """Get health metrics for all tracked models.

        Returns:
            Dict mapping model → metrics
        """
        return {model: self._get_breaker(model).metrics for model in self.circuit_breakers}

    def _get_breaker(self, model: str) -> ModelCircuitBreaker:
        """Get or create circuit breaker for model.

        Args:
            model: Model name

        Returns:
            ModelCircuitBreaker
        """
        if model not in self.circuit_breakers:
            self.circuit_breakers[model] = ModelCircuitBreaker(
                model,
                error_threshold=self.error_threshold,
                recovery_timeout_sec=self.recovery_timeout_sec,
            )

        return self.circuit_breakers[model]

    def _record_fallback(self, primary: str, fallback: str) -> None:
        """Record fallback occurrence.

        Args:
            primary: Primary model
            fallback: Fallback model used
        """
        self.fallback_count += 1
        self.fallback_history.append((primary, fallback, time.time()))

        logger.info(
            f"Fallback #{self.fallback_count}: {primary} → {fallback} "
            f"(total degradations: {self.fallback_count})"
        )

    def get_fallback_stats(self) -> dict:
        """Get fallback statistics.

        Returns:
            Dict with fallback counts and patterns
        """
        stats = {
            "total_fallbacks": self.fallback_count,
            "recent_fallbacks": len(
                [ts for _, _, ts in self.fallback_history if time.time() - ts < 3600]
            ),
        }

        # Count fallback patterns
        patterns: dict[tuple[str, str], int] = {}
        for primary, fallback, _ in self.fallback_history:
            key = (primary, fallback)
            patterns[key] = patterns.get(key, 0) + 1

        stats["fallback_patterns"] = dict(patterns)

        return stats

    def reset(self) -> None:
        """Reset all circuit breakers (testing only)."""
        for breaker in self.circuit_breakers.values():
            breaker.reset()
        self.fallback_count = 0
        self.fallback_history.clear()


def get_fallback_strategy() -> ModelFallbackStrategy:
    """Get or create singleton fallback strategy."""
    global _fallback_strategy
    if _fallback_strategy is None:
        _fallback_strategy = ModelFallbackStrategy()
    return _fallback_strategy


def reset_fallback_strategy() -> None:
    """Reset fallback strategy singleton (testing only)."""
    global _fallback_strategy
    _fallback_strategy = None


# Global singleton
_fallback_strategy: ModelFallbackStrategy | None = None
