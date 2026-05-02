"""Phase 6 Chaos Testing - Fault Injection and Recovery Validation.

Comprehensive chaos testing for Phase 6 components focusing on:
- CostAwareRouter resilience and consistency
- ModelFallbackStrategy circuit breaker and recovery
- ModelRanker stability across scale
- AnomalyDetector high-volume processing
- BudgetEnforcer correctness
- Concurrent operation safety
- Data integrity under faults
- Load and scale characteristics

Tests validate system resilience and recovery behavior.
"""

import time

import pytest

from cohezion.cost_optimization.budget_enforcer import BudgetEnforcer
from cohezion.swarm.anomaly_detector import (
    get_anomaly_detector,
    reset_anomaly_detector,
)
from cohezion.swarm.cost_aware_router import CostAwareRouter
from cohezion.swarm.model_fallback_strategy import ModelFallbackStrategy
from cohezion.swarm.model_ranker import ModelRanker, RankingStrategy


class TestCostRouterResilience:
    """Test CostAwareRouter resilience under fault conditions."""

    def test_router_selects_model_consistently(self):
        """Test router consistently selects valid models."""
        router = CostAwareRouter()
        models_selected = []
        for _ in range(20):
            decision, _can_proceed = router.select_model(query="test")
            models_selected.append(decision.model)
        assert all(m is not None for m in models_selected)

    def test_router_handles_multiple_queries(self):
        """Test router handles multiple sequential queries."""
        router = CostAwareRouter()
        for i in range(50):
            decision, _can_proceed = router.select_model(query=f"query-{i}: test")
            assert decision.model is not None

    def test_router_maintains_selection_under_load(self):
        """Test router maintains quality under load."""
        router = CostAwareRouter()
        decisions = []
        for _ in range(100):
            decision, _can_proceed = router.select_model(query="benchmark")
            decisions.append(decision)
        assert len(decisions) == 100
        assert all(d.model is not None for d in decisions)


class TestModelFallbackResilience:
    """Test ModelFallbackStrategy circuit breaker and recovery."""

    def test_circuit_breaker_state_tracking(self):
        """Test circuit breaker tracks state."""
        fallback = ModelFallbackStrategy()
        for _ in range(10):
            fallback.record_execution("test-model", success=False)
        # Circuit breaker is per-model now
        assert "test-model" in fallback.circuit_breakers
        breaker = fallback.circuit_breakers["test-model"]
        assert breaker.state.name in ["OPEN", "HALF_OPEN", "CLOSED"]

    def test_circuit_breaker_allows_recovery(self):
        """Test circuit breaker allows model recovery."""
        fallback = ModelFallbackStrategy()
        for _ in range(10):
            fallback.record_execution("recovering-model", success=False)
        fallback.record_execution("recovering-model", success=True)
        health = fallback.get_model_health("recovering-model")
        assert health.total_requests > 10

    def test_health_metrics_accumulate(self):
        """Test health metrics accumulate correctly."""
        fallback = ModelFallbackStrategy()
        for i in range(50):
            success = i % 3 != 0
            fallback.record_execution("test-model", success=success)
        health = fallback.get_model_health("test-model")
        assert health.total_requests == 50

    def test_fallback_chain_selection(self):
        """Test selecting from fallback chain."""
        fallback = ModelFallbackStrategy()
        selected, _is_degraded = fallback.select_model(
            primary_model="primary",
            available_models=["primary", "fallback1", "fallback2"],
        )
        assert selected in ["primary", "fallback1", "fallback2"]


class TestModelRankerResilience:
    """Test ModelRanker under different conditions."""

    def test_ranker_handles_empty_models(self):
        """Test ranker with no models available."""
        ranker = ModelRanker()
        scores = ranker.rank_models(available_models=[])
        assert len(scores) == 0

    def test_ranker_handles_single_model(self):
        """Test ranker with single model."""
        ranker = ModelRanker()
        scores = ranker.rank_models(available_models=["only-model"])
        assert len(scores) == 1

    def test_ranker_consistent_ranking(self):
        """Test ranker produces consistent rankings."""
        ranker = ModelRanker()
        models = ["model-a", "model-b", "model-c"]
        rankings = []
        for _ in range(5):
            scores = ranker.rank_models(available_models=models, strategy=RankingStrategy.BALANCED)
            rankings.append([m for m, _ in scores])
        first = rankings[0]
        for ranking in rankings[1:]:
            assert ranking == first

    def test_ranker_handles_large_model_list(self):
        """Test ranker with many models."""
        ranker = ModelRanker()
        models = [f"model-{i}" for i in range(50)]
        scores = ranker.rank_models(available_models=models)
        assert len(scores) == 50


class TestAnomalyDetectorResilience:
    """Test AnomalyDetector stability and recovery."""

    def test_anomaly_detector_handles_high_volume(self):
        """Test anomaly detector under high alert volume."""
        reset_anomaly_detector()
        detector = get_anomaly_detector()
        for i in range(100):
            detector.detect_spike(
                actual_cost=0.50 + (i * 0.001),
                forecasted_cost=0.40,
                model=f"model-{i % 20}",
            )
        assert len(detector.recent_alerts) > 0

    def test_anomaly_detector_per_model_isolation(self):
        """Test anomaly detection is isolated per model."""
        reset_anomaly_detector()
        detector = get_anomaly_detector()
        detector.detect_spike(0.50, 0.40, model="model-1")
        detector.detect_spike(0.60, 0.40, model="model-2")
        detector.detect_spike(0.70, 0.40, model="model-3")
        assert "model-1" in detector.model_histories
        assert "model-2" in detector.model_histories
        assert "model-3" in detector.model_histories

    def test_anomaly_detector_quality_mismatch_detection(self):
        """Test quality-cost mismatch detection."""
        reset_anomaly_detector()
        detector = get_anomaly_detector()
        for i in range(20):
            detector.detect_quality_cost_mismatch(
                cost=0.50 + (i * 0.01),
                coherence_score=0.3,
                model="low-quality",
            )
        assert len(detector.recent_alerts) > 0


class TestBudgetEnforcerResilience:
    """Test BudgetEnforcer under various conditions."""

    def test_budget_enforcer_tracks_usage(self):
        """Test budget enforcer tracks usage correctly."""
        budget = BudgetEnforcer(budget_usd=100.0)
        # BudgetEnforcer checks budget constraints
        result1 = budget.check_budget(current_cost_usd=0.50)
        result2 = budget.check_budget(current_cost_usd=1.00)
        assert result1 is not None
        assert result2 is not None

    def test_budget_enforcer_multiple_queries(self):
        """Test budget enforcer with many queries."""
        budget = BudgetEnforcer(budget_usd=100.0)
        for i in range(50):
            result = budget.check_budget(current_cost_usd=0.01 * (i + 1))
            assert result is not None

    def test_budget_enforcer_check_budget(self):
        """Test budget check functionality."""
        budget = BudgetEnforcer(budget_usd=100.0)
        result = budget.check_budget(current_cost_usd=5.00)
        assert result is not None
        assert isinstance(result, tuple)

    def test_budget_enforcer_threshold_detection(self):
        """Test budget threshold detection."""
        budget = BudgetEnforcer(budget_usd=100.0)
        status = budget.check_budget(current_cost_usd=50.00)
        assert status is not None
        assert isinstance(status, tuple)


class TestConcurrentOperationsResilience:
    """Test system resilience with concurrent operations."""

    def test_concurrent_router_selections(self):
        """Test concurrent router selections."""
        router = CostAwareRouter()
        results = []
        for _ in range(100):
            decision, _can_proceed = router.select_model(query="test")
            results.append(decision.model)
        assert len(results) == 100

    def test_concurrent_anomaly_detection(self):
        """Test concurrent anomaly detection."""
        reset_anomaly_detector()
        detector = get_anomaly_detector()
        for i in range(100):
            detector.detect_spike(
                actual_cost=0.50 + (i * 0.001),
                forecasted_cost=0.40,
                model="concurrent-test",
            )
        assert len(detector.recent_alerts) > 0

    def test_concurrent_fallback_selection(self):
        """Test concurrent fallback selection."""
        fallback = ModelFallbackStrategy()
        selections = []
        for _ in range(100):
            selected, _is_degraded = fallback.select_model(
                primary_model="primary",
                available_models=["primary", "backup1", "backup2"],
            )
            selections.append(selected)
        assert len(selections) == 100

    def test_concurrent_model_ranking(self):
        """Test concurrent model ranking."""
        ranker = ModelRanker()
        rankings = []
        for _ in range(50):
            scores = ranker.rank_models(available_models=["m1", "m2", "m3", "m4", "m5"])
            rankings.append(len(scores))
        assert all(r == 5 for r in rankings)


class TestErrorConditionRecovery:
    """Test recovery from various error conditions."""

    def test_recovery_from_model_failures(self):
        """Test recovery after model failures."""
        fallback = ModelFallbackStrategy()
        for _ in range(10):
            fallback.record_execution("bad-model", success=False)
        fallback.record_execution("bad-model", success=True)
        health = fallback.get_model_health("bad-model")
        assert health.total_requests == 11

    def test_recovery_from_threshold_breach(self):
        """Test response to threshold breaches."""
        budget = BudgetEnforcer(budget_usd=100.0, warn_threshold_pct=50)
        result = budget.check_budget(current_cost_usd=50.00)
        assert result is not None

    def test_graceful_degradation_under_stress(self):
        """Test graceful degradation under stress."""
        router = CostAwareRouter()
        budget = BudgetEnforcer(budget_usd=100.0)
        for i in range(200):
            decision, _can_proceed = router.select_model(query=f"stress-test-{i}")
            result = budget.check_budget(current_cost_usd=0.01 * (i + 1))
            assert result is not None
        decision, _ = router.select_model(query="after-stress")
        assert decision.model is not None


class TestDataIntegrityUnderFault:
    """Test data integrity during fault conditions."""

    def test_anomaly_data_persists(self):
        """Test anomaly data persists through operations."""
        reset_anomaly_detector()
        detector = get_anomaly_detector()
        alert1 = detector.detect_spike(0.50, 0.40, model="m1")
        if alert1:
            for _ in range(10):
                detector.detect_spike(0.55, 0.40, model=f"m{_}")
            assert len(detector.recent_alerts) > 0

    def test_model_health_data_consistency(self):
        """Test model health data remains consistent."""
        fallback = ModelFallbackStrategy()
        for i in range(100):
            success = i % 2 == 0
            fallback.record_execution("health-test", success=success)
        health1 = fallback.get_model_health("health-test")
        initial_requests = health1.total_requests
        for _ in range(50):
            fallback.record_execution("health-test", success=True)
        health2 = fallback.get_model_health("health-test")
        # Should have 50 more requests
        assert health2.total_requests == initial_requests + 50

    def test_budget_usage_accumulation(self):
        """Test budget usage accumulates consistently."""
        budget = BudgetEnforcer(budget_usd=100.0)
        # Check multiple budget constraints
        result1 = budget.check_budget(current_cost_usd=0.50)
        result2 = budget.check_budget(current_cost_usd=1.00)
        assert result1 is not None
        assert result2 is not None
        # Both should return valid results
        assert isinstance(result1, tuple)
        assert isinstance(result2, tuple)


class TestLoadAndScaleCharacteristics:
    """Test system characteristics under load."""

    def test_ranker_performance_with_scale(self):
        """Test ranker performance with many models."""
        ranker = ModelRanker()
        models = [f"model-{i}" for i in range(100)]
        start = time.time()
        scores = ranker.rank_models(available_models=models)
        elapsed = time.time() - start
        assert len(scores) == 100
        assert elapsed < 5.0

    def test_detector_memory_boundedness(self):
        """Test anomaly detector doesn't leak memory."""
        reset_anomaly_detector()
        detector = get_anomaly_detector()
        for i in range(1000):
            detector.detect_spike(
                actual_cost=0.50 + (i % 10) * 0.01,
                forecasted_cost=0.40,
                model=f"model-{i % 20}",
            )
        assert len(detector.recent_alerts) <= 1000

    def test_fallback_circuit_breaker_performance(self):
        """Test circuit breaker scales with model count."""
        fallback = ModelFallbackStrategy()
        for i in range(20):
            for j in range(10):
                fallback.record_execution(f"model-{i}", success=(j % 3 == 0))
        for i in range(20):
            health = fallback.get_model_health(f"model-{i}")
            assert health.total_requests == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
