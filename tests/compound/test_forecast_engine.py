"""Tests for cost forecasting engine.

Tests cover:
- Time-series forecasting (24h, 7d, 30d)
- Exponential smoothing accuracy
- Confidence interval calculations
- Anomaly detection for unusual spend patterns
- Historical data aggregation
"""

import time

import pytest

from cohezion.cost_optimization.forecast_engine import (
    AnomalyScore,
    Forecast,
    ForecastEngine,
    get_forecast_engine,
    reset_forecast_engine,
)


class TestForecastDataStructures:
    """Test forecast data structures."""

    def test_forecast_initialization(self):
        """Test Forecast creation."""
        forecast = Forecast(
            timestamp=time.time(),
            horizon_hours=24,
            predicted_cost_usd=100.0,
            confidence_interval_lower=90.0,
            confidence_interval_upper=110.0,
            confidence_pct=90.0,
            method="exponential_smoothing",
        )

        assert forecast.horizon_hours == 24
        assert forecast.predicted_cost_usd == 100.0
        assert forecast.confidence_pct == 90.0

    def test_forecast_to_dict(self):
        """Test Forecast serialization."""
        forecast = Forecast(
            timestamp=time.time(),
            horizon_hours=24,
            predicted_cost_usd=100.0,
            confidence_interval_lower=90.0,
            confidence_interval_upper=110.0,
            confidence_pct=90.0,
            method="exponential_smoothing",
        )

        data = forecast.to_dict()
        assert data["predicted_cost_usd"] == 100.0
        assert data["method"] == "exponential_smoothing"

    def test_anomaly_score_initialization(self):
        """Test AnomalyScore creation."""
        score = AnomalyScore(
            timestamp=time.time(),
            current_rate_usd_per_hour=0.15,
            expected_rate_usd_per_hour=0.10,
            deviation_pct=50.0,
            anomaly_score=75.0,
            is_anomaly=True,
            anomaly_type="spike",
        )

        assert score.is_anomaly is True
        assert score.anomaly_type == "spike"
        assert 0 <= score.anomaly_score <= 100


class TestForecastEngine:
    """Test forecast engine functionality."""

    @pytest.fixture
    def engine(self):
        """Create forecast engine."""
        return ForecastEngine(alpha=0.3, anomaly_threshold_pct=20.0)

    def test_engine_initialization(self, engine):
        """Test ForecastEngine initialization."""
        assert engine.alpha == 0.3
        assert engine.anomaly_threshold_pct == 20.0
        assert len(engine.history) == 0

    def test_add_single_observation(self, engine):
        """Test adding a single observation."""
        engine.add_observation(
            timestamp=time.time(),
            cost_usd=10.0,
            duration_hours=1.0,
        )

        assert len(engine.history) == 1
        assert engine.smoothed_level == 10.0

    def test_add_multiple_observations(self, engine):
        """Test adding multiple observations."""
        timestamps = [time.time() - i * 3600 for i in range(10, 0, -1)]

        for i, ts in enumerate(timestamps):
            engine.add_observation(
                timestamp=ts,
                cost_usd=10.0 + i,
                duration_hours=1.0,
            )

        assert len(engine.history) == 10
        assert engine.smoothed_level > 0

    def test_forecast_with_insufficient_data(self, engine):
        """Test forecast returns None with insufficient data."""
        engine.add_observation(time.time(), 10.0, 1.0)

        forecast = engine.forecast(24)

        assert forecast is None

    def test_forecast_24_hours(self, engine):
        """Test 24-hour forecast."""
        # Add observations
        for i in range(10):
            engine.add_observation(
                timestamp=time.time() - (10 - i) * 3600,
                cost_usd=10.0 + i,
                duration_hours=1.0,
            )

        forecast = engine.forecast(horizon_hours=24)

        assert forecast is not None
        assert forecast.horizon_hours == 24
        assert forecast.predicted_cost_usd > 0
        assert forecast.confidence_interval_lower < forecast.predicted_cost_usd
        assert forecast.predicted_cost_usd < forecast.confidence_interval_upper

    def test_forecast_7_days(self, engine):
        """Test 7-day forecast."""
        for i in range(10):
            engine.add_observation(
                timestamp=time.time() - (10 - i) * 3600,
                cost_usd=10.0,
                duration_hours=1.0,
            )

        forecast = engine.forecast(horizon_hours=7 * 24)

        assert forecast is not None
        assert forecast.horizon_hours == 7 * 24

    def test_forecast_30_days(self, engine):
        """Test 30-day forecast."""
        for i in range(10):
            engine.add_observation(
                timestamp=time.time() - (10 - i) * 3600,
                cost_usd=10.0,
                duration_hours=1.0,
            )

        forecast = engine.forecast(horizon_hours=30 * 24)

        assert forecast is not None
        assert forecast.horizon_hours == 30 * 24

    def test_forecast_summary(self, engine):
        """Test forecast summary across all horizons."""
        for i in range(10):
            engine.add_observation(
                timestamp=time.time() - (10 - i) * 3600,
                cost_usd=10.0 + i,
                duration_hours=1.0,
            )

        summary = engine.forecast_summary()

        assert summary is not None
        assert summary.forecast_24h_usd > 0
        assert summary.forecast_7d_usd > 0
        assert summary.forecast_30d_usd > 0
        assert summary.confidence_24h > 0

    def test_confidence_intervals(self, engine):
        """Test confidence intervals are calculated correctly."""
        for i in range(10):
            engine.add_observation(
                timestamp=time.time() - (10 - i) * 3600,
                cost_usd=10.0,
                duration_hours=1.0,
            )

        forecast_90 = engine.forecast(24, confidence_pct=90.0)
        forecast_95 = engine.forecast(24, confidence_pct=95.0)

        assert forecast_90 is not None
        assert forecast_95 is not None
        assert forecast_90.confidence_pct == 90.0
        assert forecast_95.confidence_pct == 95.0


class TestAnomalyDetection:
    """Test anomaly detection functionality."""

    @pytest.fixture
    def engine_with_history(self):
        """Create engine with historical data."""
        engine = ForecastEngine(alpha=0.3, anomaly_threshold_pct=20.0)

        # Add stable historical data: $10/hour consistently
        for i in range(20):
            engine.add_observation(
                timestamp=time.time() - (20 - i) * 3600,
                cost_usd=10.0,
                duration_hours=1.0,
            )

        return engine

    def test_normal_rate_no_anomaly(self, engine_with_history):
        """Test normal spend rate has no anomaly."""
        score = engine_with_history.detect_anomaly(current_rate_usd_per_hour=10.0)

        assert score.is_anomaly is False
        assert score.anomaly_type == "normal"
        assert score.anomaly_score < 50

    def test_spike_detection(self, engine_with_history):
        """Test spike in spend rate is detected."""
        score = engine_with_history.detect_anomaly(
            current_rate_usd_per_hour=15.0  # 50% increase
        )

        assert score.is_anomaly is True
        assert score.anomaly_type == "spike"
        assert score.anomaly_score > 50

    def test_drop_detection(self, engine_with_history):
        """Test drop in spend rate is detected."""
        score = engine_with_history.detect_anomaly(
            current_rate_usd_per_hour=5.0  # 50% decrease
        )

        assert score.is_anomaly is True
        assert score.anomaly_type == "drop"

    def test_anomaly_scoring_0_to_100(self, engine_with_history):
        """Test anomaly score is bounded 0-100."""
        for rate in [5.0, 10.0, 15.0, 20.0, 30.0]:
            score = engine_with_history.detect_anomaly(rate)
            assert 0 <= score.anomaly_score <= 100

    def test_threshold_behavior(self):
        """Test anomaly threshold control."""
        engine_strict = ForecastEngine(alpha=0.3, anomaly_threshold_pct=10.0)
        engine_lenient = ForecastEngine(alpha=0.3, anomaly_threshold_pct=30.0)

        # Add history to both
        for engine in [engine_strict, engine_lenient]:
            for i in range(10):
                engine.add_observation(
                    timestamp=time.time() - (10 - i) * 3600,
                    cost_usd=10.0,
                    duration_hours=1.0,
                )

        # Test at 15% deviation
        score_strict = engine_strict.detect_anomaly(11.5)
        score_lenient = engine_lenient.detect_anomaly(11.5)

        assert score_strict.is_anomaly is True  # 15% > 10% threshold
        assert score_lenient.is_anomaly is False  # 15% < 30% threshold


class TestHistoryStatistics:
    """Test historical data statistics."""

    @pytest.fixture
    def engine_with_data(self):
        """Create engine with diverse data."""
        engine = ForecastEngine()

        # Add varied observations
        rates = [5.0, 7.0, 10.0, 8.0, 12.0, 15.0, 10.0, 9.0, 11.0, 13.0]
        for i, rate in enumerate(rates):
            engine.add_observation(
                timestamp=time.time() - (len(rates) - i) * 3600,
                cost_usd=rate,
                duration_hours=1.0,
            )

        return engine

    def test_history_stats_structure(self, engine_with_data):
        """Test history statistics have correct structure."""
        stats = engine_with_data.get_history_stats()

        assert "min_rate_usd_per_hour" in stats
        assert "max_rate_usd_per_hour" in stats
        assert "mean_rate_usd_per_hour" in stats
        assert "total_cost_usd" in stats
        assert "observation_count" in stats

    def test_history_stats_values(self, engine_with_data):
        """Test history statistics values are correct."""
        stats = engine_with_data.get_history_stats()

        assert stats["min_rate_usd_per_hour"] == 5.0
        assert stats["max_rate_usd_per_hour"] == 15.0
        assert stats["observation_count"] == 10
        assert stats["total_cost_usd"] == 100.0


class TestSingleton:
    """Test singleton pattern."""

    def test_singleton_instance(self):
        """Test singleton returns same instance."""
        reset_forecast_engine()

        engine1 = get_forecast_engine()
        engine2 = get_forecast_engine()

        assert engine1 is engine2

    def test_reset_singleton(self):
        """Test singleton reset."""
        engine1 = get_forecast_engine()

        reset_forecast_engine()

        engine2 = get_forecast_engine()

        assert engine1 is not engine2
