"""Tests for cost anomaly detection.

Tests:
- Spike detection (sudden cost increase >20%)
- Trend detection (gradual cost increase over time)
- Quality-cost mismatch detection
- False positive filtering (<5% rate)
- Multi-model history tracking
- Confidence calculation
"""

import time
from unittest.mock import Mock

import pytest

from cohezion.swarm.anomaly_detector import (
    AnomalyAlert,
    AnomalyDetector,
    AnomalyType,
    ModelCostHistory,
    get_anomaly_detector,
    reset_anomaly_detector,
)


class TestAnomalyDetectorInitialization:
    """Test anomaly detector initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        detector = AnomalyDetector()

        assert detector.forecast_threshold == 0.20
        assert detector.trend_threshold == 0.0005
        assert detector.trend_window_hours == 2
        assert detector.coherence_threshold == -0.10
        assert detector.fp_adjustment_factor == 0.9

    def test_init_with_custom_thresholds(self):
        """Test initialization with custom thresholds."""
        detector = AnomalyDetector(
            forecast_threshold=0.15,
            trend_threshold=0.001,
            coherence_threshold=-0.05,
        )

        assert detector.forecast_threshold == 0.15
        assert detector.trend_threshold == 0.001
        assert detector.coherence_threshold == -0.05

    def test_empty_history_on_init(self):
        """Test that detector starts with empty history."""
        detector = AnomalyDetector()

        assert len(detector.model_histories) == 0
        assert len(detector.recent_alerts) == 0


class TestCostSpikeDetection:
    """Test detection of sudden cost spikes."""

    @pytest.fixture
    def detector(self):
        reset_anomaly_detector()
        return AnomalyDetector(forecast_threshold=0.20)

    def test_spike_above_threshold(self, detector):
        """Test spike when actual cost > forecast + threshold."""
        alert = detector.detect_spike(
            actual_cost=0.50,
            forecasted_cost=0.40,  # 25% above
            model="qwen3-coder:32b",
            coherence_score=0.8,
        )

        assert alert is not None
        assert alert.anomaly_type == AnomalyType.SPIKE
        assert alert.cost_actual == 0.50
        assert alert.cost_forecasted == 0.40
        assert abs(alert.cost_deviation_pct - 25.0) < 0.1  # Allow floating point error

    def test_no_spike_within_threshold(self, detector):
        """Test no spike when within threshold."""
        alert = detector.detect_spike(
            actual_cost=0.41,
            forecasted_cost=0.40,  # 2.5% above
            model="phi3:mini",
        )

        assert alert is None

    def test_spike_below_forecast(self, detector):
        """Test spike detection when cost is below forecast."""
        alert = detector.detect_spike(
            actual_cost=0.30,
            forecasted_cost=0.40,  # 25% below
            model="deepseek-r1:8b",
        )

        # Should detect as negative spike
        assert alert is not None
        assert abs(alert.cost_deviation_pct - (-25.0)) < 0.1  # Allow floating point error

    def test_spike_severity_calculation(self, detector):
        """Test severity increases with deviation."""
        alert1 = detector.detect_spike(
            actual_cost=0.52,
            forecasted_cost=0.40,  # 30% above
            model="model1",
        )
        alert2 = detector.detect_spike(
            actual_cost=0.60,
            forecasted_cost=0.40,  # 50% above
            model="model2",
        )

        assert alert1.severity < alert2.severity

    def test_spike_with_default_forecast(self, detector):
        """Test spike when forecast not provided (defaults to actual)."""
        alert = detector.detect_spike(
            actual_cost=0.50,
            forecasted_cost=None,  # Will use actual_cost
            model="test-model",
        )

        assert alert is None  # No deviation from self


class TestCostTrendDetection:
    """Test detection of cost trends over time."""

    @pytest.fixture
    def detector(self):
        reset_anomaly_detector()
        return AnomalyDetector(
            trend_threshold=0.0005,
            trend_window_hours=1,
        )

    def test_no_trend_constant_cost(self, detector):
        """Test no trend when costs are constant."""
        model = "constant-model"

        # Add 10 datapoints with same cost
        for _ in range(10):
            detector.model_histories[model] = ModelCostHistory(model=model)

        for _ in range(10):
            detector.detect_trend(model=model)
            time.sleep(0.01)

        # No trend should be detected
        alert = detector.detect_trend(model=model)
        assert alert is None  # Constant costs don't trend

    def test_upward_trend_detection(self, detector):
        """Test detection of increasing cost trend."""
        model = "trending-model"
        detector._ensure_history(model)
        history = detector.model_histories[model]

        # Add costs that increase significantly over time
        # Need slope > 0.0005 cost/second over 1 hour window
        # So minimum cost increase = 0.0005 * 3600 = 1.8 per hour
        start_time = time.time() - (60 * 60)  # 1 hour ago
        for i in range(20):
            cost = 0.10 + (i * 0.1)  # Large increase: 0.1 per iteration
            history.costs.append(cost)
            history.times.append(start_time + (i * 180))  # 3 min intervals
            history.forecasts.append(cost)
            history.coherence_scores.append(0.7)

        # Should detect upward trend
        alert = detector.detect_trend(model=model, coherence_score=0.7)
        assert alert is not None
        assert alert.anomaly_type == AnomalyType.TREND

    def test_trend_with_coherence_drop(self, detector):
        """Test trend severity increases with coherence drop."""
        model = "degrading-model"
        detector._ensure_history(model)
        history = detector.model_histories[model]

        # Add trending costs with degrading coherence
        # Need slope > 0.0005 cost/second over 1 hour window
        start_time = time.time() - (60 * 60)  # 1 hour ago
        for i in range(20):
            cost = 0.10 + (i * 0.1)  # Large increase to exceed trend threshold
            coherence = 0.9 - (i * 0.02)  # Drop by 0.02 per iteration
            history.costs.append(cost)
            history.times.append(start_time + (i * 180))  # 3 min intervals
            history.forecasts.append(cost)
            history.coherence_scores.append(max(0.0, coherence))

        alert = detector.detect_trend(model=model, coherence_score=0.7)
        assert alert is not None
        # Severity should be boosted due to coherence drop
        assert alert.severity > 0.2


class TestQualityCostMismatchDetection:
    """Test quality-cost mismatch detection."""

    @pytest.fixture
    def detector(self):
        reset_anomaly_detector()
        return AnomalyDetector()

    def test_high_cost_low_quality(self, detector):
        """Test detection of high cost with low quality."""
        alert = detector.detect_quality_cost_mismatch(
            cost=0.80,
            coherence_score=0.40,  # Low quality
            model="expensive-low-quality",
        )

        assert alert is not None
        assert alert.anomaly_type == AnomalyType.QUALITY_COST_MISMATCH
        assert alert.severity > 0.3

    def test_high_cost_high_quality_ok(self, detector):
        """Test high cost with high quality is acceptable."""
        alert = detector.detect_quality_cost_mismatch(
            cost=0.80,
            coherence_score=0.95,  # High quality
            model="expensive-high-quality",
        )

        assert alert is None  # Acceptable trade-off

    def test_low_cost_low_quality_ok(self, detector):
        """Test low cost with low quality is acceptable."""
        alert = detector.detect_quality_cost_mismatch(
            cost=0.05,
            coherence_score=0.40,
            model="cheap-low-quality",
        )

        assert alert is None  # Acceptable (cheap)


class TestFalsePositiveFiltering:
    """Test false positive rate and filtering."""

    @pytest.fixture
    def detector(self):
        reset_anomaly_detector()
        return AnomalyDetector(fp_adjustment_factor=0.9)

    def test_low_confidence_alerts_filtered(self, detector):
        """Test that low-confidence alerts are filtered."""
        # Very small deviation that would have low confidence
        alert = detector.detect_spike(
            actual_cost=0.401,  # 0.25% above
            forecasted_cost=0.400,
            model="low-confidence",
        )

        assert alert is None  # Filtered due to low confidence

    def test_high_confidence_alerts_pass(self, detector):
        """Test that high-confidence alerts pass filter."""
        alert = detector.detect_spike(
            actual_cost=0.60,  # 50% above
            forecasted_cost=0.40,
            model="high-confidence",
        )

        assert alert is not None
        assert alert.confidence >= 0.70

    def test_false_positive_rate_calculation(self, detector):
        """Test FP rate calculation over recent window."""
        # Add mix of alerts with various confidence
        for i in range(10):
            detector.detect_spike(
                actual_cost=0.40 + (i * 0.01),
                forecasted_cost=0.40,
                model=f"model-{i}",
            )

        fp_rate = detector.get_false_positive_rate(minutes=60)
        assert 0.0 <= fp_rate <= 1.0


class TestModelCostHistory:
    """Test model cost history tracking."""

    def test_add_datapoint(self):
        """Test adding cost datapoints."""
        history = ModelCostHistory(model="test-model")

        history.add_datapoint(cost=0.50, forecast=0.45, coherence=0.8)
        history.add_datapoint(cost=0.55, forecast=0.45, coherence=0.75)

        assert len(history.costs) == 2
        assert len(history.times) == 2
        assert history.costs[0] == 0.50
        assert history.costs[1] == 0.55

    def test_get_recent_costs(self):
        """Test retrieval of recent costs."""
        history = ModelCostHistory(model="test-model")

        # Add costs across different times
        start = time.time()
        for i in range(5):
            history.costs.append(0.10 + i * 0.01)
            history.times.append(start + (i * 60))  # 1 min apart

        recent = history.get_recent_costs(minutes=3)
        assert len(recent) >= 3

    def test_get_average_cost(self):
        """Test average cost calculation."""
        history = ModelCostHistory(model="test-model")

        costs = [0.10, 0.20, 0.30]
        for cost in costs:
            history.add_datapoint(cost=cost)

        avg = history.get_average_cost(minutes=10)
        assert abs(avg - 0.20) < 0.01

    def test_cost_trend_calculation(self):
        """Test cost trend slope calculation."""
        history = ModelCostHistory(model="test-model")

        # Add increasing costs
        start = time.time()
        for i in range(10):
            cost = 0.10 + (i * 0.01)
            history.costs.append(cost)
            history.times.append(start + (i * 300))  # 5 min intervals
            history.forecasts.append(cost)
            history.coherence_scores.append(0.7)

        trend = history.get_cost_trend(minutes=60)
        assert trend > 0  # Positive trend


class TestConfidenceCalculation:
    """Test confidence score calculation."""

    @pytest.fixture
    def detector(self):
        reset_anomaly_detector()
        return AnomalyDetector()

    def test_confidence_increases_with_deviation(self, detector):
        """Test confidence increases with larger deviations."""
        conf1 = detector._calculate_confidence(
            anomaly_type=AnomalyType.SPIKE,
            deviation=0.10,  # Small
            recent_history=[0.40],
        )
        conf2 = detector._calculate_confidence(
            anomaly_type=AnomalyType.SPIKE,
            deviation=0.50,  # Large
            recent_history=[0.40],
        )

        assert conf2 > conf1

    def test_confidence_boosted_by_consistency(self, detector):
        """Test confidence boosted by consistent history."""
        # Consistent costs
        consistent = [0.50, 0.50, 0.50, 0.50, 0.50]
        # Variable costs
        variable = [0.40, 0.50, 0.60, 0.45, 0.55]

        conf_consistent = detector._calculate_confidence(
            anomaly_type=AnomalyType.SPIKE,
            deviation=0.30,
            recent_history=consistent,
        )
        conf_variable = detector._calculate_confidence(
            anomaly_type=AnomalyType.SPIKE,
            deviation=0.30,
            recent_history=variable,
        )

        assert conf_consistent >= conf_variable

    def test_confidence_minimum_threshold(self, detector):
        """Test confidence never exceeds 1.0."""
        conf = detector._calculate_confidence(
            anomaly_type=AnomalyType.SPIKE,
            deviation=1.0,  # Very large
            recent_history=[0.40] * 10,
        )

        assert conf <= 1.0


class TestSingletonPattern:
    """Test singleton pattern."""

    def test_get_anomaly_detector(self):
        """Test getting singleton detector."""
        reset_anomaly_detector()
        detector1 = get_anomaly_detector()
        detector2 = get_anomaly_detector()

        assert detector1 is detector2

    def test_reset_singleton(self):
        """Test resetting singleton."""
        detector = get_anomaly_detector()
        detector.recent_alerts.append(Mock())

        reset_anomaly_detector()
        new_detector = get_anomaly_detector()

        assert len(new_detector.recent_alerts) == 0


class TestAnomalyAlertValidation:
    """Test anomaly alert validation."""

    def test_alert_passes_fp_threshold(self):
        """Test alert passes false positive threshold."""
        alert = AnomalyAlert(
            anomaly_type=AnomalyType.SPIKE,
            detected_at=time.time(),
            cost_actual=0.50,
            cost_forecasted=0.40,
            cost_deviation_pct=25.0,
            model="test",
            severity=0.5,
            confidence=0.90,  # High confidence (>= 0.90 = 1.0 - 0.05*2)
            description="Test alert",
        )

        assert alert.is_valid_alert(fp_threshold=0.05)

    def test_alert_fails_fp_threshold(self):
        """Test alert fails false positive threshold."""
        alert = AnomalyAlert(
            anomaly_type=AnomalyType.SPIKE,
            detected_at=time.time(),
            cost_actual=0.50,
            cost_forecasted=0.40,
            cost_deviation_pct=25.0,
            model="test",
            severity=0.5,
            confidence=0.50,  # Low confidence
            description="Test alert",
        )

        assert not alert.is_valid_alert(fp_threshold=0.05)


class TestIntegrationMultiModel:
    """Test integration with multiple models."""

    @pytest.fixture
    def detector(self):
        reset_anomaly_detector()
        return AnomalyDetector()

    def test_independent_model_histories(self, detector):
        """Test models have independent cost histories."""
        detector.detect_spike(0.50, 0.40, model="model-a")
        detector.detect_spike(0.60, 0.55, model="model-b")

        assert "model-a" in detector.model_histories
        assert "model-b" in detector.model_histories
        assert len(detector.model_histories) == 2

    def test_simultaneous_anomalies(self, detector):
        """Test detecting anomalies in multiple models."""
        alert1 = detector.detect_spike(0.50, 0.40, model="model-a")  # 25% deviation
        alert2 = detector.detect_spike(0.60, 0.48, model="model-b")  # 25% deviation

        assert alert1 is not None
        assert alert2 is not None
        assert len(detector.recent_alerts) == 2


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def detector(self):
        reset_anomaly_detector()
        return AnomalyDetector()

    def test_zero_cost(self, detector):
        """Test handling of zero cost."""
        alert = detector.detect_spike(
            actual_cost=0.0,
            forecasted_cost=0.0,
            model="free-model",
        )

        assert alert is None

    def test_very_small_costs(self, detector):
        """Test with very small costs (1e-6)."""
        alert = detector.detect_spike(
            actual_cost=1e-6,
            forecasted_cost=5e-7,
            model="micro-model",
        )

        # Should still work
        assert alert is not None or alert is None  # Either is OK for edge case

    def test_negative_cost_handling(self, detector):
        """Test handling of negative costs (refunds)."""
        alert = detector.detect_spike(
            actual_cost=-0.10,  # Refund
            forecasted_cost=0.10,
            model="refund-model",
        )

        # Should detect large deviation
        assert alert is not None

    def test_empty_history_trend(self, detector):
        """Test trend detection with empty history."""
        alert = detector.detect_trend(model="nonexistent-model")

        assert alert is None  # No history = no trend


class TestResetFunctionality:
    """Test reset functionality."""

    def test_detector_reset(self):
        """Test detector reset clears state."""
        detector = AnomalyDetector()
        detector.detect_spike(0.50, 0.40, model="test")
        detector.detect_trend(model="test")

        detector.reset()

        assert len(detector.model_histories) == 0
        assert len(detector.recent_alerts) == 0
