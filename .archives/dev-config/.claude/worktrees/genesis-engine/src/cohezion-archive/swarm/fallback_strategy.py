"""Graceful fallback strategy with circuit breaker pattern and cost preservation.

Features:
- Intelligent fallback chain: primary → secondary → emergency
- Circuit breaker pattern with three states: CLOSED, OPEN, HALF_OPEN
- Model health tracking (latency, error rate)
- Cost-aware fallback selection (prefer cheapest available)
- Non-blocking design (graceful degradation)
- Comprehensive logging and metrics

Architecture:
  Execution Request
       ↓
  Check Circuit Breaker Status
       ├→ CLOSED: Use model
       ├→ HALF_OPEN: Allow probe request
       └→ OPEN: Fallback
       ↓
  Select Fallback Model
       ├→ Check cost (prefer cheaper if available)
       ├→ Check quality loss acceptable
       └→ Try chain: secondary → emergency
       ↓
  Execute with Selected Model
       ↓
  Record Metrics (health, cost, degradation)

Cost Preservation Strategy:
  1. Primary unavailable → Try secondary (potentially cheaper)
  2. Secondary unavailable → Try emergency (most reliable)
  3. All unavailable → Use cheapest fallback
  4. Track cost savings during degradation periods

Usage:
    fallback = FallbackStrategy()
    model, degraded, cost = fallback.execute_with_fallback(
        primary_model="deepseek-r1:8b",
        query="Complex analysis task",
        available_models=["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b"],
        cost_tracker=tracker
    )
    if degraded:
        logger.info(f"Fallback to {model}, cost savings preserved")
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states for model availability."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Model unavailable, reject requests
    HALF_OPEN = "half_open"  # Testing if model recovered


@dataclass
class ModelHealthMetrics:
    """Health metrics tracking for a model."""

    model: str
    error_count: int = 0  # Consecutive errors
    success_count: int = 0  # Consecutive successes
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
            elif seconds_since_error < 600:  # Error 5-10 min ago
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
            latency_threshold_ms: Latency threshold for triggering open (default: 5000ms)
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

        # Update average latency (exponential moving average)
        if self.metrics.avg_latency_ms == 0.0:
            self.metrics.avg_latency_ms = latency_ms
        else:
            self.metrics.avg_latency_ms = 0.7 * self.metrics.avg_latency_ms + 0.3 * latency_ms

        # If HALF_OPEN and succeeded, go back to CLOSED
        if self.state == CircuitBreakerState.HALF_OPEN:
            if self.metrics.success_count >= self.success_threshold:
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

        # If too many consecutive errors, open circuit
        if self.metrics.error_count >= self.error_threshold:
            logger.warning(
                f"Circuit breaker: {self.model} - {self.metrics.error_count} consecutive errors threshold reached"
            )
            self._transition_to_open()

        # If error rate too high (only check after enough samples)
        if self.metrics.total_requests >= 10 and self.metrics.error_rate >= self.error_rate_threshold:
            logger.warning(
                f"Circuit breaker: {self.model} - error rate {self.metrics.error_rate:.1%} exceeds threshold"
            )
            self._transition_to_open()

    def record_latency_spike(self) -> None:
        """Record latency spike (slow response detected)."""
        if self.metrics.last_latency_ms > self.latency_threshold_ms:
            logger.warning(
                f"Circuit breaker: {self.model} - latency spike {self.metrics.last_latency_ms:.0f}ms exceeds threshold"
            )
            # Don't immediately open, but count as minor issue
            # Could transition to HALF_OPEN if repeated

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
                f"error_rate={self.metrics.error_rate:.1%}"
            )
            self.state = CircuitBreakerState.OPEN
            self.opened_at = time.time()

    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state (testing recovery)."""
        if self.state != CircuitBreakerState.HALF_OPEN:
            logger.info(
                f"Circuit breaker HALF_OPEN for {self.model}: testing recovery after {self.recovery_timeout_sec}s"
            )
            self.state = CircuitBreakerState.HALF_OPEN
            self.metrics.error_count = 0
            self.metrics.success_count = 0

    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state (recovered)."""
        if self.state != CircuitBreakerState.CLOSED:
            downtime_sec = time.time() - (self.opened_at or 0)
            logger.info(f"Circuit breaker CLOSED for {self.model}: recovered after {downtime_sec:.1f}s downtime")
            self.state = CircuitBreakerState.CLOSED
            self.opened_at = None
            self.metrics.error_count = 0
            self.metrics.success_count = 0

    def reset(self) -> None:
        """Reset circuit breaker (testing only)."""
        self.state = CircuitBreakerState.CLOSED
        self.opened_at = None
        self.metrics = ModelHealthMetrics(model=self.model)


class FallbackStrategy:
    """Intelligent fallback strategy with circuit breaker and cost preservation.

    Manages graceful degradation when models become unavailable:
    1. Monitor model health (latency, error rate)
    2. Detect unavailability via circuit breaker
    3. Fallback to next-cheapest available model
    4. Preserve cost savings during degradation
    5. Auto-recovery when model becomes healthy

    Features:
    - Non-blocking: Always has fallback available
    - Cost-aware: Prefers cheaper alternatives if quality acceptable
    - Intelligent: Learns from past degradations
    - Graceful: Transparent to caller (degraded flag indicates state)
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

    # Model costs (per 1K tokens) - local models are free
    MODEL_COSTS = {
        "phi3:mini": 0.0,
        "qwen3-coder:32b": 0.0,
        "deepseek-r1:8b": 0.0,
        "gemma3:4b": 0.0,
        "mistral:7b": 0.0,
        "llama4-scout": 0.0,
    }

    def __init__(
        self,
        latency_threshold_ms: float = 5000.0,
        error_rate_threshold: float = 0.10,
        circuit_reset_time_sec: float = 300.0,
        min_quality_loss: float = 0.10,
    ):
        """Initialize fallback strategy.

        Args:
            latency_threshold_ms: Latency threshold to trigger circuit (default: 5000ms)
            error_rate_threshold: Error rate threshold (default: 10%)
            circuit_reset_time_sec: Time before circuit reset attempt (default: 300s)
            min_quality_loss: Max acceptable quality loss in fallback (0.0-1.0)
        """
        self.latency_threshold_ms = latency_threshold_ms
        self.error_rate_threshold = error_rate_threshold
        self.circuit_reset_time_sec = circuit_reset_time_sec
        self.min_quality_loss = min_quality_loss

        # Circuit breakers per model
        self.circuit_breakers: dict[str, CircuitBreaker] = {}

        # Degradation tracking
        self.fallback_count: int = 0
        self.fallback_history: list[FallbackEvent] = []
        self.total_cost_saved: float = 0.0

    def execute_with_fallback(
        self,
        primary_model: str,
        available_models: list[str],
        model_costs: dict[str, float] | None = None,
        quality_scores: dict[str, float] | None = None,
    ) -> tuple[str, bool, float]:
        """Execute with fallback support and cost preservation.

        Args:
            primary_model: Primary model choice
            available_models: All available models to consider
            model_costs: Optional cost override (per 1K tokens)
            quality_scores: Optional quality score override

        Returns:
            Tuple of:
            - selected_model: Model to use
            - is_degraded: True if using fallback
            - cost_saving_usd: Estimated cost saving from fallback (0 if no fallback)
        """
        quality_scores = quality_scores or self.MODEL_QUALITY
        model_costs = model_costs or self.MODEL_COSTS

        # Check if primary available
        primary_breaker = self._get_breaker(primary_model)
        if primary_breaker.allow_request():
            return primary_model, False, 0.0

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
            quality_loss = (
                (primary_quality - fallback_quality) / max(primary_quality, 0.01)
                if primary_quality > fallback_quality
                else 0.0
            )

            if quality_loss <= self.min_quality_loss:
                # Calculate cost saving
                primary_cost = model_costs.get(primary_model, 0.0)
                fallback_cost = model_costs.get(fallback_model, 0.0)
                cost_saving = max(0.0, primary_cost - fallback_cost)

                # Use fallback
                self._record_fallback(
                    primary_model,
                    fallback_model,
                    reason="quality_acceptable",
                    cost_saving=cost_saving,
                    quality_loss=quality_loss,
                )
                return fallback_model, True, cost_saving

        # No acceptable fallback, try emergency (deepseek if available and not primary)
        if primary_model != "deepseek-r1:8b" and "deepseek-r1:8b" in available_models:
            emergency_breaker = self._get_breaker("deepseek-r1:8b")
            if emergency_breaker.allow_request():
                primary_cost = model_costs.get(primary_model, 0.0)
                fallback_cost = model_costs.get("deepseek-r1:8b", 0.0)
                cost_saving = max(0.0, primary_cost - fallback_cost)

                logger.warning(
                    f"Using emergency fallback: {primary_model} unavailable, "
                    f"using deepseek-r1:8b (quality loss unacceptable but necessary)"
                )
                self._record_fallback(
                    primary_model,
                    "deepseek-r1:8b",
                    reason="emergency_fallback",
                    cost_saving=cost_saving,
                    quality_loss=0.2,  # Estimated quality loss
                )
                return "deepseek-r1:8b", True, cost_saving

        # Last resort: use any available model that's not the primary
        available_non_primary = [m for m in available_models if m != primary_model]
        if available_non_primary:
            # Choose cheapest available
            selected = min(
                available_non_primary,
                key=lambda m: model_costs.get(m, 0.0),
            )
            primary_cost = model_costs.get(primary_model, 0.0)
            fallback_cost = model_costs.get(selected, 0.0)
            cost_saving = max(0.0, primary_cost - fallback_cost)

            logger.error(f"All models degraded or primary unavailable, using fallback: {selected}")
            self._record_fallback(
                primary_model,
                selected,
                reason="all_degraded",
                cost_saving=cost_saving,
                quality_loss=0.3,
            )
            return selected, True, cost_saving

        # Absolute last resort: return primary anyway
        logger.error(f"No alternative models available, forced to use primary: {primary_model}")
        return primary_model, True, 0.0

    def detect_model_unavailability(self, model: str, latency_ms: float, error_occurred: bool) -> bool:
        """Detect if model is becoming unavailable.

        Args:
            model: Model name
            latency_ms: Request latency
            error_occurred: Whether request errored

        Returns:
            True if model should be considered unavailable
        """
        breaker = self._get_breaker(model)

        if error_occurred:
            breaker.record_error(latency_ms)
            return breaker.state != CircuitBreakerState.CLOSED

        # Check latency
        if latency_ms > self.latency_threshold_ms:
            breaker.record_latency_spike()

        breaker.record_success(latency_ms)
        return False

    def get_fallback_chain(self, primary_model: str) -> list[str]:
        """Get fallback chain for a primary model.

        Args:
            primary_model: Primary model name

        Returns:
            List of fallback models in order of preference
        """
        return self.DEFAULT_FALLBACK_CHAINS.get(primary_model, [])

    def reset_circuit_breaker(self, model: str) -> None:
        """Reset circuit breaker for a model (recovery mechanism).

        Args:
            model: Model name to reset
        """
        breaker = self._get_breaker(model)
        old_state = breaker.state
        breaker.reset()
        logger.info(f"Circuit breaker reset for {model}: {old_state} → CLOSED")

    def preserve_cost_savings(
        self,
        primary_model: str,
        available_models: list[str],
        model_costs: dict[str, float] | None = None,
    ) -> tuple[str, float]:
        """Choose cheapest working fallback to preserve cost savings.

        Args:
            primary_model: Primary (usually most expensive) model
            available_models: Available models to consider
            model_costs: Optional cost override

        Returns:
            Tuple of (selected_model, cost_saving_usd)
        """
        model_costs = model_costs or self.MODEL_COSTS

        # Sort by cost (cheapest first)
        available_sorted = sorted(
            available_models,
            key=lambda m: model_costs.get(m, 0.0),
        )

        for model in available_sorted:
            breaker = self._get_breaker(model)
            if breaker.allow_request():
                cost_saving = max(
                    0.0,
                    model_costs.get(primary_model, 0.0) - model_costs.get(model, 0.0),
                )
                return model, cost_saving

        # Fallback to most available
        return available_sorted[0], 0.0

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
            breaker.record_error(latency_ms)

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
            Dict mapping model name → metrics
        """
        return {model: breaker.metrics for model, breaker in self.circuit_breakers.items()}

    def get_fallback_stats(self) -> dict:
        """Get fallback statistics.

        Returns:
            Dict with fallback counts, patterns, and cost savings
        """
        stats = {
            "total_fallbacks": self.fallback_count,
            "recent_fallbacks": len([e for e in self.fallback_history if time.time() - e.timestamp < 3600]),
            "total_cost_saved_usd": self.total_cost_saved,
        }

        # Count fallback patterns
        patterns: dict[tuple[str, str], int] = {}
        for event in self.fallback_history:
            key = (event.primary_model, event.fallback_model)
            patterns[key] = patterns.get(key, 0) + 1

        stats["fallback_patterns"] = dict(patterns)

        return stats

    def _get_breaker(self, model: str) -> CircuitBreaker:
        """Get or create circuit breaker for model.

        Args:
            model: Model name

        Returns:
            CircuitBreaker
        """
        if model not in self.circuit_breakers:
            self.circuit_breakers[model] = CircuitBreaker(
                model,
                error_threshold=2,  # Open after 2 consecutive errors
                recovery_timeout_sec=self.circuit_reset_time_sec,
                error_rate_threshold=self.error_rate_threshold,
                latency_threshold_ms=self.latency_threshold_ms,
            )

        return self.circuit_breakers[model]

    def _record_fallback(
        self,
        primary: str,
        fallback: str,
        reason: str = "unavailable",
        cost_saving: float = 0.0,
        quality_loss: float = 0.0,
    ) -> None:
        """Record fallback occurrence.

        Args:
            primary: Primary model
            fallback: Fallback model used
            reason: Reason for fallback
            cost_saving: USD saved by using fallback
            quality_loss: Quality loss percentage (0.0-1.0)
        """
        self.fallback_count += 1
        event = FallbackEvent(
            timestamp=time.time(),
            primary_model=primary,
            fallback_model=fallback,
            reason=reason,
            cost_saved_usd=cost_saving,
            quality_loss=quality_loss,
        )
        self.fallback_history.append(event)
        self.total_cost_saved += cost_saving

        logger.info(
            f"Fallback #{self.fallback_count}: {primary} → {fallback} "
            f"(reason: {reason}, cost_saved: ${cost_saving:.6f}, quality_loss: {quality_loss:.1%})"
        )

    def reset(self) -> None:
        """Reset all circuit breakers and history (testing only)."""
        for breaker in self.circuit_breakers.values():
            breaker.reset()
        self.fallback_count = 0
        self.fallback_history.clear()
        self.total_cost_saved = 0.0


# Singleton instance
_fallback_strategy: FallbackStrategy | None = None


def get_fallback_strategy() -> FallbackStrategy:
    """Get or create singleton fallback strategy.

    Returns:
        FallbackStrategy singleton instance
    """
    global _fallback_strategy
    if _fallback_strategy is None:
        _fallback_strategy = FallbackStrategy()
    return _fallback_strategy


def reset_fallback_strategy() -> None:
    """Reset fallback strategy singleton (testing only)."""
    global _fallback_strategy
    _fallback_strategy = None
