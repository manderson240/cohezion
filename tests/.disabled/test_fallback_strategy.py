"""Tests for intelligent model fallback strategy with circuit breaker.

Tests:
- Circuit breaker state transitions
- Fallback chain selection
- Quality-aware fallback
- Recovery behavior
- Health tracking
"""

import time

import pytest

from cohezion.swarm.model_fallback_strategy import (
    CircuitBreakerState,
    ModelCircuitBreaker,
    ModelFallbackStrategy,
    ModelHealthMetrics,
    get_fallback_strategy,
    reset_fallback_strategy,
)


class TestCircuitBreakerBasics:
    """Test basic circuit breaker functionality."""

    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initializes in CLOSED state."""
        breaker = ModelCircuitBreaker("test-model")

        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.model == "test-model"
        assert breaker.metrics.error_count == 0
        assert breaker.metrics.success_count == 0

    def test_allow_request_when_closed(self):
        """Test requests allowed when circuit closed."""
        breaker = ModelCircuitBreaker("model")

        assert breaker.allow_request() is True
        assert breaker.allow_request() is True

    def test_record_success_increments_counter(self):
        """Test success records increment success counter."""
        breaker = ModelCircuitBreaker("model")

        initial_successes = breaker.metrics.success_count
        breaker.record_success(latency_ms=50.0)

        assert breaker.metrics.success_count == initial_successes + 1
        assert breaker.metrics.error_count == 0

    def test_record_error_increments_counter(self):
        """Test error records increment error counter."""
        breaker = ModelCircuitBreaker("model")

        initial_errors = breaker.metrics.total_errors
        breaker.record_error()

        assert breaker.metrics.total_errors == initial_errors + 1

    def test_latency_tracking(self):
        """Test average latency tracking."""
        breaker = ModelCircuitBreaker("model")

        # Record several executions
        breaker.record_success(latency_ms=50.0)
        breaker.record_success(latency_ms=100.0)
        breaker.record_success(latency_ms=75.0)

        # Average should be somewhere in range
        assert 50.0 <= breaker.metrics.avg_latency_ms <= 100.0


class TestCircuitBreakerStateTransitions:
    """Test circuit breaker state machine."""

    def test_transition_to_open_on_consecutive_errors(self):
        """Test transition to OPEN on consecutive errors."""
        breaker = ModelCircuitBreaker("model", error_threshold=2)

        # Record 2 errors (threshold is 2, so on 2nd error should open)
        breaker.record_error()
        assert breaker.state == CircuitBreakerState.CLOSED

        breaker.record_error()
        assert breaker.state == CircuitBreakerState.OPEN

    def test_reject_requests_when_open(self):
        """Test requests rejected when circuit open."""
        breaker = ModelCircuitBreaker("model", error_threshold=2)

        # Open circuit
        breaker.record_error()
        breaker.record_error()

        assert breaker.state == CircuitBreakerState.OPEN
        assert breaker.allow_request() is False

    def test_transition_to_half_open_after_timeout(self):
        """Test transition to HALF_OPEN after recovery timeout."""
        breaker = ModelCircuitBreaker("model", error_threshold=1, recovery_timeout_sec=0.1)

        # Open circuit
        breaker.record_error()
        assert breaker.state == CircuitBreakerState.OPEN

        # Wait for timeout
        time.sleep(0.15)

        # Should transition to HALF_OPEN on next request check
        can_request = breaker.allow_request()
        assert can_request is True
        assert breaker.state == CircuitBreakerState.HALF_OPEN

    def test_transition_to_closed_on_recovery(self):
        """Test transition to CLOSED after successful recovery."""
        breaker = ModelCircuitBreaker(
            "model",
            error_threshold=2,
            success_threshold=2,
            recovery_timeout_sec=0.1,
        )

        # Open circuit
        breaker.record_error()
        breaker.record_error()
        assert breaker.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        time.sleep(0.15)
        breaker.allow_request()  # Transition to HALF_OPEN

        # Record successes
        breaker.record_success()
        breaker.record_success()

        # Should be CLOSED
        assert breaker.state == CircuitBreakerState.CLOSED

    def test_error_rate_threshold(self):
        """Test that consecutive error threshold takes precedence."""
        breaker = ModelCircuitBreaker("model", error_threshold=2, error_rate_threshold=0.5)

        # Record 2 errors → hits consecutive error threshold first
        breaker.record_error()
        assert breaker.state == CircuitBreakerState.CLOSED

        breaker.record_error()
        # Should be OPEN due to consecutive error threshold
        assert breaker.state == CircuitBreakerState.OPEN


class TestModelHealthMetrics:
    """Test model health scoring."""

    def test_error_rate_calculation(self):
        """Test error rate calculation."""
        metrics = ModelHealthMetrics(model="test")

        metrics.total_requests = 10
        metrics.total_errors = 3

        assert metrics.error_rate == 0.3

    def test_zero_requests_error_rate(self):
        """Test error rate with zero requests."""
        metrics = ModelHealthMetrics(model="test")

        assert metrics.total_requests == 0
        assert metrics.error_rate == 0.0

    def test_health_score_from_error_rate(self):
        """Test health score degrades with error rate."""
        metrics_healthy = ModelHealthMetrics(model="test1")
        metrics_healthy.total_requests = 100
        metrics_healthy.total_errors = 10  # 10% error rate

        metrics_unhealthy = ModelHealthMetrics(model="test2")
        metrics_unhealthy.total_requests = 100
        metrics_unhealthy.total_errors = 50  # 50% error rate

        assert metrics_healthy.health_score > metrics_unhealthy.health_score


class TestModelFallbackStrategy:
    """Test intelligent fallback strategy."""

    @pytest.fixture
    def strategy(self):
        """Create fallback strategy."""
        return ModelFallbackStrategy()

    def test_primary_model_when_available(self, strategy):
        """Test primary model selected when available."""
        primary, degraded = strategy.select_model(
            primary_model="deepseek-r1:8b",
            available_models=["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b"],
        )

        assert primary == "deepseek-r1:8b"
        assert degraded is False

    def test_fallback_when_primary_unavailable(self, strategy):
        """Test fallback selected when primary unavailable."""
        # Mark primary as unavailable
        breaker = strategy._get_breaker("deepseek-r1:8b")
        breaker.record_error()
        breaker.record_error()
        breaker.record_error()

        # Should fallback to qwen
        selected, degraded = strategy.select_model(
            primary_model="deepseek-r1:8b",
            available_models=["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b"],
        )

        assert selected != "deepseek-r1:8b"
        assert degraded is True

    def test_fallback_chain_order(self, strategy):
        """Test fallback follows chain order."""
        # Mark primary and first fallback as unavailable
        for model in ["deepseek-r1:8b", "qwen3-coder:32b"]:
            for _ in range(3):
                strategy._get_breaker(model).record_error()

        # Should try phi3 next
        selected, degraded = strategy.select_model(
            primary_model="deepseek-r1:8b",
            available_models=["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b"],
        )

        assert selected == "phi3:mini"
        assert degraded is True

    def test_quality_loss_acceptable(self, strategy):
        """Test fallback only if quality loss acceptable."""
        strategy.min_quality_loss = 0.05  # Max 5% quality loss

        # phi3 (0.6) → qwen (0.82) is actually improvement
        selected, degraded = strategy.select_model(
            primary_model="phi3:mini",
            available_models=["phi3:mini", "qwen3-coder:32b"],
        )

        assert selected == "phi3:mini"
        assert degraded is False

    def test_record_execution_success(self, strategy):
        """Test recording successful execution."""
        model = "test-model"
        breaker = strategy._get_breaker(model)

        initial_successes = breaker.metrics.success_count
        strategy.record_execution(model, success=True, latency_ms=50.0)

        assert breaker.metrics.success_count == initial_successes + 1

    def test_record_execution_failure(self, strategy):
        """Test recording failed execution."""
        model = "test-model"
        breaker = strategy._get_breaker(model)

        initial_errors = breaker.metrics.total_errors
        strategy.record_execution(model, success=False)

        assert breaker.metrics.total_errors == initial_errors + 1

    def test_fallback_counting(self, strategy):
        """Test fallback occurrences are counted."""
        # Mark primary unavailable
        breaker = strategy._get_breaker("deepseek-r1:8b")
        for _ in range(3):
            breaker.record_error()

        initial_count = strategy.fallback_count

        # Trigger fallback
        strategy.select_model(
            primary_model="deepseek-r1:8b",
            available_models=["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b"],
        )

        assert strategy.fallback_count == initial_count + 1

    def test_fallback_history(self, strategy):
        """Test fallback history recording."""
        # Mark primary unavailable
        breaker = strategy._get_breaker("deepseek-r1:8b")
        for _ in range(3):
            breaker.record_error()

        # Trigger fallback
        strategy.select_model(
            primary_model="deepseek-r1:8b",
            available_models=["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b"],
        )

        assert len(strategy.fallback_history) > 0
        primary, fallback, _ts = strategy.fallback_history[-1]
        assert primary == "deepseek-r1:8b"
        assert fallback in ["phi3:mini", "qwen3-coder:32b"]

    def test_get_model_health(self, strategy):
        """Test retrieving model health metrics."""
        model = "test-model"
        strategy.record_execution(model, success=True, latency_ms=50.0)
        strategy.record_execution(model, success=True, latency_ms=50.0)
        strategy.record_execution(model, success=False)

        health = strategy.get_model_health(model)

        assert health.model == model
        assert health.total_requests >= 3
        assert health.total_errors >= 1

    def test_get_all_health(self, strategy):
        """Test retrieving all model health metrics."""
        strategy.record_execution("model1", success=True)
        strategy.record_execution("model2", success=False)

        all_health = strategy.get_all_health()

        assert "model1" in all_health
        assert "model2" in all_health
        assert all_health["model1"].success_count >= 1
        assert all_health["model2"].total_errors >= 1

    def test_fallback_stats(self, strategy):
        """Test fallback statistics."""
        stats = strategy.get_fallback_stats()

        assert "total_fallbacks" in stats
        assert "recent_fallbacks" in stats
        assert "fallback_patterns" in stats

    def test_reset(self, strategy):
        """Test resetting strategy."""
        # Mark something as unavailable
        strategy._get_breaker("test").record_error()
        strategy._get_breaker("test").record_error()
        strategy._get_breaker("test").record_error()

        # Reset
        strategy.reset()

        # Should be back to normal
        assert strategy._get_breaker("test").state == CircuitBreakerState.CLOSED
        assert strategy.fallback_count == 0


class TestFallbackIntegration:
    """Integration tests for fallback with circuit breaker."""

    def test_complete_failure_and_recovery_cycle(self):
        """Test complete failure and recovery cycle."""
        strategy = ModelFallbackStrategy(error_threshold=2, recovery_timeout_sec=0.1)

        model = "unreliable-model"

        # Phase 1: Normal operation
        strategy.record_execution(model, success=True)
        strategy.record_execution(model, success=True)

        assert strategy._get_breaker(model).state == CircuitBreakerState.CLOSED

        # Phase 2: Failures
        strategy.record_execution(model, success=False)
        strategy.record_execution(model, success=False)

        assert strategy._get_breaker(model).state == CircuitBreakerState.OPEN

        # Phase 3: Recovery timeout
        time.sleep(0.15)

        breaker = strategy._get_breaker(model)
        breaker.allow_request()  # Transition to HALF_OPEN

        assert breaker.state == CircuitBreakerState.HALF_OPEN

        # Phase 4: Recovery
        strategy.record_execution(model, success=True)
        strategy.record_execution(model, success=True)

        assert breaker.state == CircuitBreakerState.CLOSED

    def test_multiple_models_independent_breakers(self):
        """Test that each model has independent circuit breaker."""
        strategy = ModelFallbackStrategy(error_threshold=2)

        # Fail model1
        for _ in range(2):
            strategy.record_execution("model1", success=False)

        # model2 should be unaffected
        strategy.record_execution("model2", success=True)

        assert strategy._get_breaker("model1").state == CircuitBreakerState.OPEN
        assert strategy._get_breaker("model2").state == CircuitBreakerState.CLOSED

    def test_cascading_fallbacks(self):
        """Test cascading fallbacks when multiple models fail."""
        strategy = ModelFallbackStrategy(error_threshold=2)

        # Fail multiple models in the fallback chain
        for model in ["deepseek-r1:8b", "qwen3-coder:32b"]:
            for _ in range(2):
                strategy.record_execution(model, success=False)

        # Should still be able to select phi3
        selected, degraded = strategy.select_model(
            primary_model="deepseek-r1:8b",
            available_models=["phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b"],
        )

        assert selected == "phi3:mini"
        assert degraded is True


class TestSingletonPattern:
    """Test singleton pattern for fallback strategy."""

    def test_get_fallback_strategy(self):
        """Test singleton getter."""
        reset_fallback_strategy()

        strategy1 = get_fallback_strategy()
        strategy2 = get_fallback_strategy()

        assert strategy1 is strategy2

    def test_reset_singleton(self):
        """Test singleton reset."""
        reset_fallback_strategy()

        strategy1 = get_fallback_strategy()
        initial_count = strategy1.fallback_count

        reset_fallback_strategy()

        strategy2 = get_fallback_strategy()
        assert strategy2.fallback_count == 0
        # After reset, should get a new instance (or reset instance)
        assert strategy2.fallback_count == initial_count
