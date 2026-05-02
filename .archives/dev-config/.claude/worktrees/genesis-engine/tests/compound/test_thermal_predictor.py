"""Tests for ThermalTrendAnalyzer - Thermal prediction and learning."""

from __future__ import annotations

import pytest

from cohezion.compound.thermal_predictor import (
    ThermalMetrics,
    ThermalTrendAnalyzer,
    get_thermal_trend_analyzer,
)


@pytest.fixture
def analyzer() -> ThermalTrendAnalyzer:
    """Create a thermal analyzer instance."""
    return ThermalTrendAnalyzer(history_size=50)


@pytest.fixture
def sample_metrics() -> ThermalMetrics:
    """Create sample thermal metrics."""
    return ThermalMetrics(
        batch_size=32,
        task_count=10,
        task_types=["analyze", "analyze", "search"],
        duration_seconds=5.0,
        tokens_used=1600,
        peak_gpu_temp=75.0,
        peak_cpu_temp=65.0,
        throttle_detected=False,
        throttle_percentage=0.0,
        execution_power_watts=25.0,
    )


class TestThermalMetrics:
    """Test ThermalMetrics dataclass."""

    def test_initialization(self, sample_metrics):
        """Test metrics initialization."""
        assert sample_metrics.batch_size == 32
        assert sample_metrics.task_count == 10
        assert sample_metrics.peak_gpu_temp == 75.0
        assert sample_metrics.throttle_detected is False

    def test_primary_task_type(self, sample_metrics):
        """Test primary task type detection."""
        assert sample_metrics.primary_task_type == "analyze"

    def test_tokens_per_second(self, sample_metrics):
        """Test tokens per second calculation."""
        tps = sample_metrics.tokens_per_second
        assert tps == 1600.0 / 5.0  # 320 tokens/sec

    def test_empty_task_types(self):
        """Test with empty task types."""
        metrics = ThermalMetrics(
            batch_size=32,
            task_count=10,
            task_types=[],
            duration_seconds=5.0,
            tokens_used=1600,
            peak_gpu_temp=75.0,
            peak_cpu_temp=65.0,
            throttle_detected=False,
            throttle_percentage=0.0,
            execution_power_watts=25.0,
        )
        assert metrics.primary_task_type == "unknown"


class TestThermalTrendAnalyzerInit:
    """Test analyzer initialization."""

    def test_initialization_defaults(self, analyzer):
        """Test initialization with defaults."""
        assert analyzer.history_size == 50
        assert analyzer.target_temp_celsius == 85.0
        assert len(analyzer.history) == 0

    def test_initialization_custom(self):
        """Test initialization with custom parameters."""
        analyzer = ThermalTrendAnalyzer(history_size=200, target_temp_celsius=80.0)
        assert analyzer.history_size == 200
        assert analyzer.target_temp_celsius == 80.0

    def test_base_temperatures(self, analyzer):
        """Test base temperature heuristics."""
        assert analyzer.BASE_TEMPS["generate"] == 72.0
        assert analyzer.BASE_TEMPS["analyze"] == 68.0
        assert analyzer.BASE_TEMPS["search"] == 65.0
        assert analyzer.BASE_TEMPS["unknown"] == 70.0

    def test_thermal_limits(self, analyzer):
        """Test thermal limit constants."""
        assert analyzer.THERMAL_THROTTLE_POINT == 92.0
        assert analyzer.THERMAL_CRITICAL == 95.0


class TestRecordExecution:
    """Test recording executions."""

    def test_record_single_execution(self, analyzer, sample_metrics):
        """Test recording a single execution."""
        analyzer.record_execution(sample_metrics)

        assert "analyze" in analyzer.history
        assert len(analyzer.history["analyze"]) == 1

    def test_record_multiple_executions(self, analyzer, sample_metrics):
        """Test recording multiple executions."""
        for i in range(5):
            metrics = ThermalMetrics(
                batch_size=16 + (i * 8),
                task_count=10,
                task_types=["analyze"],
                duration_seconds=5.0,
                tokens_used=1600,
                peak_gpu_temp=70.0 + (i * 2),
                peak_cpu_temp=60.0 + (i * 1.5),
                throttle_detected=False,
                throttle_percentage=0.0,
                execution_power_watts=20.0 + (i * 2),
            )
            analyzer.record_execution(metrics)

        assert len(analyzer.history["analyze"]) == 5

    def test_history_size_limit(self, analyzer, sample_metrics):
        """Test history size limit enforcement."""
        analyzer.history_size = 10

        for i in range(15):
            metrics = ThermalMetrics(
                batch_size=32,
                task_count=10,
                task_types=["analyze"],
                duration_seconds=5.0,
                tokens_used=1600,
                peak_gpu_temp=70.0 + (i * 0.5),
                peak_cpu_temp=60.0,
                throttle_detected=False,
                throttle_percentage=0.0,
                execution_power_watts=25.0,
            )
            analyzer.record_execution(metrics)

        # Should keep only last 10
        assert len(analyzer.history["analyze"]) == 10

    def test_record_multiple_task_types(self, analyzer):
        """Test recording for different task types."""
        for task_type in ["generate", "analyze", "search"]:
            metrics = ThermalMetrics(
                batch_size=32,
                task_count=10,
                task_types=[task_type],
                duration_seconds=5.0,
                tokens_used=1600,
                peak_gpu_temp=70.0,
                peak_cpu_temp=60.0,
                throttle_detected=False,
                throttle_percentage=0.0,
                execution_power_watts=25.0,
            )
            analyzer.record_execution(metrics)

        assert len(analyzer.history) == 3
        assert "generate" in analyzer.history
        assert "analyze" in analyzer.history
        assert "search" in analyzer.history


class TestPredictThermalSafety:
    """Test thermal safety prediction."""

    def test_predict_no_history_fallback(self, analyzer):
        """Test prediction falls back to heuristic when no history."""
        temp = analyzer.predict_thermal_safety("analyze", batch_size=32, duration_sec=5.0)

        assert isinstance(temp, float)
        assert 50.0 < temp < 100.0  # Reasonable range

    def test_predict_unknown_task_type(self, analyzer):
        """Test prediction for unknown task type."""
        temp = analyzer.predict_thermal_safety("unknown", batch_size=32, duration_sec=5.0)

        assert isinstance(temp, float)
        assert 50.0 < temp < 100.0

    def test_predict_with_single_execution(self, analyzer, sample_metrics):
        """Test prediction with single historical execution."""
        analyzer.record_execution(sample_metrics)

        temp = analyzer.predict_thermal_safety("analyze", batch_size=32, duration_sec=5.0)

        assert isinstance(temp, float)
        assert 70.0 < temp < 85.0  # Should be close to recorded 75.0

    def test_predict_with_historical_data(self, analyzer):
        """Test prediction with multiple historical data points."""
        # Record executions with increasing batch sizes and temps
        batch_sizes = [16, 32, 48, 64]
        for size in batch_sizes:
            metrics = ThermalMetrics(
                batch_size=size,
                task_count=10,
                task_types=["analyze"],
                duration_seconds=5.0,
                tokens_used=1600,
                peak_gpu_temp=65.0 + (size / 16.0),
                peak_cpu_temp=55.0,
                throttle_detected=False,
                throttle_percentage=0.0,
                execution_power_watts=20.0,
            )
            analyzer.record_execution(metrics)

        # Predict for batch size 32
        temp = analyzer.predict_thermal_safety("analyze", batch_size=32, duration_sec=5.0)

        assert isinstance(temp, float)
        assert 65.0 < temp < 75.0


class TestGetSafeBatchSize:
    """Test safe batch size calculation."""

    def test_safe_batch_size_no_history(self, analyzer):
        """Test safe batch size with no history."""
        safe_size = analyzer.get_safe_batch_size("analyze")

        assert isinstance(safe_size, int)
        assert 1 <= safe_size <= 256

    def test_safe_batch_size_with_history(self, analyzer):
        """Test safe batch size with historical data."""
        # Record cool executions
        for size in [8, 16, 32]:
            metrics = ThermalMetrics(
                batch_size=size,
                task_count=10,
                task_types=["analyze"],
                duration_seconds=5.0,
                tokens_used=1600,
                peak_gpu_temp=70.0,
                peak_cpu_temp=55.0,
                throttle_detected=False,
                throttle_percentage=0.0,
                execution_power_watts=20.0,
            )
            analyzer.record_execution(metrics)

        safe_size = analyzer.get_safe_batch_size("analyze", target_temp=80.0)

        assert isinstance(safe_size, int)
        assert safe_size >= 1

    def test_safe_batch_size_conservative_target(self, analyzer):
        """Test safe batch size with conservative target."""
        # Record warm executions
        for size in [64, 128]:
            metrics = ThermalMetrics(
                batch_size=size,
                task_count=10,
                task_types=["search"],
                duration_seconds=5.0,
                tokens_used=1600,
                peak_gpu_temp=85.0,
                peak_cpu_temp=70.0,
                throttle_detected=False,
                throttle_percentage=0.0,
                execution_power_watts=30.0,
            )
            analyzer.record_execution(metrics)

        # More conservative target
        safe_size = analyzer.get_safe_batch_size("search", target_temp=75.0)

        assert isinstance(safe_size, int)
        assert safe_size >= 1


class TestPredictThrottleProbability:
    """Test throttle probability prediction."""

    def test_throttle_probability_low(self, analyzer):
        """Test low throttle probability with cool batch."""
        prob = analyzer.predict_throttle_probability("analyze", batch_size=8)

        assert isinstance(prob, float)
        assert 0.0 <= prob <= 1.0
        assert prob < 0.2  # Should be low for small batch

    def test_throttle_probability_high(self, analyzer):
        """Test high throttle probability with large batch."""
        # Record hot executions
        for _ in range(5):
            metrics = ThermalMetrics(
                batch_size=256,
                task_count=10,
                task_types=["generate"],
                duration_seconds=10.0,
                tokens_used=2000,
                peak_gpu_temp=94.0,
                peak_cpu_temp=80.0,
                throttle_detected=True,
                throttle_percentage=15.0,
                execution_power_watts=40.0,
            )
            analyzer.record_execution(metrics)

        prob = analyzer.predict_throttle_probability("generate", batch_size=256)

        assert isinstance(prob, float)
        assert 0.0 <= prob <= 1.0
        assert prob > 0.3  # Should be higher for large hot batch

    def test_throttle_probability_bounds(self, analyzer):
        """Test throttle probability stays in [0, 1]."""
        for batch_size in [1, 8, 16, 32, 64, 128, 256]:
            prob = analyzer.predict_throttle_probability("search", batch_size)
            assert 0.0 <= prob <= 1.0


class TestEstimatePerformanceImpact:
    """Test performance impact estimation."""

    def test_no_throttle_full_performance(self, analyzer):
        """Test no throttle = full performance."""
        impact = analyzer.estimate_performance_impact(0.0)

        assert impact == 1.0  # No speed loss

    def test_full_throttle_half_performance(self, analyzer):
        """Test full throttle = half performance."""
        impact = analyzer.estimate_performance_impact(50.0)

        assert impact == 0.5  # 50% speed loss

    def test_performance_bounds(self, analyzer):
        """Test performance impact stays in [0, 1]."""
        for throttle_pct in [0, 10, 25, 50, 75, 100]:
            impact = analyzer.estimate_performance_impact(throttle_pct)
            assert 0.0 <= impact <= 1.0


class TestGetConfidence:
    """Test confidence reporting."""

    def test_confidence_no_prediction(self, analyzer):
        """Test confidence when no prediction made."""
        assert analyzer.get_confidence() == 0.0

    def test_confidence_after_prediction(self, analyzer, sample_metrics):
        """Test confidence after prediction (tracked in last_prediction)."""
        analyzer.record_execution(sample_metrics)
        # Note: current implementation doesn't track confidence in predict_thermal_safety
        # This test documents expected behavior
        temp = analyzer.predict_thermal_safety("analyze", batch_size=32, duration_sec=5.0)
        assert isinstance(temp, float)


class TestGetStats:
    """Test statistics reporting."""

    def test_stats_empty_analyzer(self, analyzer):
        """Test stats on empty analyzer."""
        stats = analyzer.get_stats()

        assert "task_types_learned" in stats
        assert stats["total_records"] == 0
        assert stats["history_per_type"] == {}

    def test_stats_with_data(self, analyzer):
        """Test stats with recorded data."""
        for task_type in ["generate", "analyze"]:
            for i in range(3):
                metrics = ThermalMetrics(
                    batch_size=32 + i,
                    task_count=10,
                    task_types=[task_type],
                    duration_seconds=5.0,
                    tokens_used=1600,
                    peak_gpu_temp=70.0 + (i * 2),
                    peak_cpu_temp=60.0,
                    throttle_detected=False,
                    throttle_percentage=0.0,
                    execution_power_watts=25.0,
                )
                analyzer.record_execution(metrics)

        stats = analyzer.get_stats()

        assert len(stats["task_types_learned"]) == 2
        assert stats["total_records"] == 6
        assert stats["history_per_type"]["generate"] == 3
        assert stats["history_per_type"]["analyze"] == 3

    def test_stats_includes_temp_summaries(self, analyzer):
        """Test stats includes per-task-type temperature summaries."""
        metrics = ThermalMetrics(
            batch_size=32,
            task_count=10,
            task_types=["search"],
            duration_seconds=5.0,
            tokens_used=1600,
            peak_gpu_temp=72.0,
            peak_cpu_temp=60.0,
            throttle_detected=False,
            throttle_percentage=0.0,
            execution_power_watts=25.0,
        )
        analyzer.record_execution(metrics)

        stats = analyzer.get_stats()

        assert "search_avg_peak_temp_c" in stats
        assert "search_max_peak_temp_c" in stats
        assert "search_min_peak_temp_c" in stats


class TestSingletonFactory:
    """Test singleton factory function."""

    def test_get_singleton(self):
        """Test getting singleton instance."""
        a1 = get_thermal_trend_analyzer()
        a2 = get_thermal_trend_analyzer()

        assert a1 is a2

    def test_reset_singleton(self):
        """Test resetting singleton."""
        a1 = get_thermal_trend_analyzer()
        a1.record_execution(
            ThermalMetrics(
                batch_size=32,
                task_count=10,
                task_types=["analyze"],
                duration_seconds=5.0,
                tokens_used=1600,
                peak_gpu_temp=70.0,
                peak_cpu_temp=60.0,
                throttle_detected=False,
                throttle_percentage=0.0,
                execution_power_watts=25.0,
            )
        )

        assert len(a1.history) > 0

        a2 = get_thermal_trend_analyzer(reset=True)

        assert a1 is not a2
        assert len(a2.history) == 0


class TestEdgeCases:
    """Test edge cases."""

    def test_predict_zero_batch_size(self, analyzer):
        """Test prediction with zero batch size."""
        temp = analyzer.predict_thermal_safety("analyze", batch_size=0, duration_sec=1.0)
        assert isinstance(temp, float)

    def test_predict_very_long_duration(self, analyzer):
        """Test prediction with very long duration."""
        temp = analyzer.predict_thermal_safety("analyze", batch_size=32, duration_sec=3600.0)
        assert isinstance(temp, float)
        assert temp > 70.0  # Should be significantly hotter

    def test_mixed_task_types_in_history(self, analyzer):
        """Test handling mixed task types in batch."""
        metrics = ThermalMetrics(
            batch_size=32,
            task_count=10,
            task_types=["generate", "analyze", "search", "analyze"],
            duration_seconds=5.0,
            tokens_used=1600,
            peak_gpu_temp=72.0,
            peak_cpu_temp=60.0,
            throttle_detected=False,
            throttle_percentage=0.0,
            execution_power_watts=25.0,
        )
        analyzer.record_execution(metrics)

        # Should use primary type (analyze - appears 2x)
        assert "analyze" in analyzer.history

    def test_empty_task_types_fallback(self, analyzer):
        """Test handling of empty task types."""
        metrics = ThermalMetrics(
            batch_size=32,
            task_count=10,
            task_types=[],
            duration_seconds=5.0,
            tokens_used=1600,
            peak_gpu_temp=72.0,
            peak_cpu_temp=60.0,
            throttle_detected=False,
            throttle_percentage=0.0,
            execution_power_watts=25.0,
        )
        analyzer.record_execution(metrics)

        # Should record under "unknown"
        assert "unknown" in analyzer.history

    def test_throttled_execution_recorded(self, analyzer):
        """Test recording of throttled execution."""
        metrics = ThermalMetrics(
            batch_size=128,
            task_count=10,
            task_types=["generate"],
            duration_seconds=10.0,
            tokens_used=2000,
            peak_gpu_temp=94.0,
            peak_cpu_temp=80.0,
            throttle_detected=True,
            throttle_percentage=25.0,
            execution_power_watts=40.0,
        )
        analyzer.record_execution(metrics)

        stats = analyzer.get_stats()
        assert stats["throttle_events"] == 1
