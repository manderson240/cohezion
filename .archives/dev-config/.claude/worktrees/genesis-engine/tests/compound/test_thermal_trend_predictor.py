"""Tests for ThermalTrendPredictor - 30-minute ahead thermal forecasting.

Phase 3 Sprint 2: Predictive Thermal Throttling

Tests cover:
- Time-series collection and accuracy
- Moving average trend calculation
- Linear regression model training
- 30-minute predictions
- Confidence scoring
- Cold start heuristics
- Backward compatibility (feature flag)
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from cohezion.compound.thermal_history_persistence import (
    ThermalTimeSeriesCollector,
    get_thermal_time_series_collector,
    load_jsonl_history,
)
from cohezion.compound.thermal_trend_predictor import (
    ThermalTimeSeries,
    ThermalTrendPredictor,
    get_thermal_trend_predictor,
)


class TestThermalTimeSeries:
    """Test ThermalTimeSeries data class."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        ts = ThermalTimeSeries(
            timestamp=time.time(),
            gpu_temp_c=75.0,
            cpu_temp_c=65.0,
            gpu_clock_mhz=2800.0,
            throttle_detected=False,
        )
        assert ts.gpu_temp_c == 75.0
        assert ts.throttle_detected is False

    def test_with_context(self):
        """Test initialization with batch context."""
        ts = ThermalTimeSeries(
            timestamp=time.time(),
            gpu_temp_c=80.0,
            cpu_temp_c=70.0,
            gpu_clock_mhz=2100.0,
            throttle_detected=True,
            batch_size_recent=32,
            concurrency_level=8,
            power_watts=35.0,
        )
        assert ts.batch_size_recent == 32
        assert ts.power_watts == 35.0


class TestThermalTrendPredictor:
    """Test ThermalTrendPredictor core functionality."""

    @pytest.fixture
    def predictor(self):
        """Create a predictor instance."""
        return ThermalTrendPredictor(max_history_samples=200)

    def test_initialization(self, predictor):
        """Test predictor initialization."""
        assert predictor.history == []
        assert predictor._model_30min is None
        assert predictor._last_prediction is None

    def test_record_sample(self, predictor):
        """Test recording thermal samples."""
        ts = ThermalTimeSeries(
            timestamp=time.time(),
            gpu_temp_c=70.0,
            cpu_temp_c=60.0,
            gpu_clock_mhz=2800.0,
            throttle_detected=False,
        )
        predictor.record_sample(ts)
        assert len(predictor.history) == 1
        assert predictor.history[0].gpu_temp_c == 70.0

    def test_record_multiple_samples(self, predictor):
        """Test recording multiple samples."""
        for i in range(10):
            ts = ThermalTimeSeries(
                timestamp=time.time() + i * 60,
                gpu_temp_c=70.0 + i * 0.5,
                cpu_temp_c=60.0,
                gpu_clock_mhz=2800.0,
                throttle_detected=False,
            )
            predictor.record_sample(ts)

        assert len(predictor.history) == 10
        assert predictor.history[-1].gpu_temp_c == 74.5

    def test_history_size_limit(self, predictor):
        """Test history size capping."""
        # Record more than max_history_samples
        for i in range(250):
            ts = ThermalTimeSeries(
                timestamp=time.time() + i * 60,
                gpu_temp_c=70.0,
                cpu_temp_c=60.0,
                gpu_clock_mhz=2800.0,
                throttle_detected=False,
            )
            predictor.record_sample(ts)

        # Should be capped at 200
        assert len(predictor.history) == 200

    def test_cold_start_prediction(self, predictor):
        """Test prediction on empty history (cold start)."""
        predicted_temp, confidence = predictor.predict_temperature_ahead(30)

        assert predicted_temp == 60.0  # Cold system default
        assert confidence == 0.0

    def test_single_sample_prediction(self, predictor):
        """Test prediction with single sample."""
        ts = ThermalTimeSeries(
            timestamp=time.time(),
            gpu_temp_c=75.0,
            cpu_temp_c=65.0,
            gpu_clock_mhz=2800.0,
            throttle_detected=False,
        )
        predictor.record_sample(ts)

        predicted_temp, confidence = predictor.predict_temperature_ahead(30)

        # Should use heuristic fallback with zero trend
        assert 70.0 < predicted_temp < 80.0
        assert 0.0 < confidence <= 0.5

    def test_warming_trend_detection(self, predictor):
        """Test detection of warming trend."""
        # Create warming trend: 70 -> 75 -> 80°C over 60 minutes
        for i in range(12):  # 12 samples, 5 min apart = 60 min
            ts = ThermalTimeSeries(
                timestamp=time.time() + i * 300,  # 5 minutes apart
                gpu_temp_c=70.0 + i * 0.42,  # ~+5°C over 60 min
                cpu_temp_c=60.0,
                gpu_clock_mhz=2800.0,
                throttle_detected=False,
            )
            predictor.record_sample(ts)

        trend = predictor._calculate_moving_average_trend(30)
        assert trend > 0.0  # Warming detected

    def test_cooling_trend_detection(self, predictor):
        """Test detection of cooling trend."""
        # Create cooling trend: 80 -> 70°C
        for i in range(12):
            ts = ThermalTimeSeries(
                timestamp=time.time() + i * 300,
                gpu_temp_c=80.0 - i * 0.42,
                cpu_temp_c=60.0,
                gpu_clock_mhz=2800.0,
                throttle_detected=False,
            )
            predictor.record_sample(ts)

        trend = predictor._calculate_moving_average_trend(30)
        assert trend < 0.0  # Cooling detected

    def test_heuristic_prediction_warming(self, predictor):
        """Test heuristic prediction with warming trend."""
        current_temp = 75.0
        trend = 0.1  # Warming at 0.1°C per minute

        predicted = predictor._predict_heuristic(current_temp, trend, 30)

        # Should predict higher temp: 75 + (0.1 * 30 * damping)
        assert predicted > current_temp

    def test_moving_average_trend_calculation(self, predictor):
        """Test moving average trend calculation."""
        # Create linear warming trend
        for i in range(50):
            ts = ThermalTimeSeries(
                timestamp=time.time() + i * 60,  # 1 minute apart
                gpu_temp_c=60.0 + i * 0.05,  # Linear +0.05°C per min
                cpu_temp_c=50.0,
                gpu_clock_mhz=2800.0,
                throttle_detected=False,
            )
            predictor.record_sample(ts)

        trend = predictor._calculate_moving_average_trend(30)
        # Should detect ~0.05°C per minute trend
        assert 0.0 < trend < 0.1

    def test_confidence_heuristic_improves_with_samples(self, predictor):
        """Test that heuristic confidence increases with sample density."""
        # Few samples (low confidence)
        ts1 = ThermalTimeSeries(
            timestamp=time.time(),
            gpu_temp_c=70.0,
            cpu_temp_c=60.0,
            gpu_clock_mhz=2800.0,
            throttle_detected=False,
        )
        predictor.record_sample(ts1)
        _, confidence_low = predictor.predict_temperature_ahead(30)

        # Many samples in recent hour (higher confidence)
        for i in range(1, 12):
            ts = ThermalTimeSeries(
                timestamp=time.time() + i * 300,  # 5 min intervals
                gpu_temp_c=70.0 + i * 0.1,
                cpu_temp_c=60.0,
                gpu_clock_mhz=2800.0,
                throttle_detected=False,
            )
            predictor.record_sample(ts)

        _, confidence_high = predictor.predict_temperature_ahead(30)
        assert confidence_high > confidence_low

    def test_get_stats(self, predictor):
        """Test statistics reporting."""
        ts = ThermalTimeSeries(
            timestamp=time.time(),
            gpu_temp_c=75.0,
            cpu_temp_c=65.0,
            gpu_clock_mhz=2800.0,
            throttle_detected=False,
        )
        predictor.record_sample(ts)

        stats = predictor.get_stats()
        assert stats["total_samples"] == 1
        assert stats["avg_gpu_temp_c"] == 75.0
        assert stats["max_gpu_temp_c"] == 75.0
        assert stats["min_gpu_temp_c"] == 75.0

    def test_model_training(self, predictor):
        """Test 30-minute model training."""
        # Create realistic data with 30-min intervals
        base_time = time.time()
        for i in range(30):  # 30 samples over 15 hours
            # Add sample at time T
            ts1 = ThermalTimeSeries(
                timestamp=base_time + i * 1800,  # 30 min apart
                gpu_temp_c=70.0 + (i % 10) * 0.5,
                cpu_temp_c=60.0,
                gpu_clock_mhz=2800.0,
                throttle_detected=False,
            )
            predictor.record_sample(ts1)

            # Add sample at time T+30min
            ts2 = ThermalTimeSeries(
                timestamp=base_time + i * 1800 + 1800,
                gpu_temp_c=70.0 + ((i + 1) % 10) * 0.5,
                cpu_temp_c=60.0,
                gpu_clock_mhz=2800.0,
                throttle_detected=False,
            )
            predictor.record_sample(ts2)

        predictor.train_30min_model()

        assert predictor._model_30min is not None
        assert "slope" in predictor._model_30min
        assert "intercept" in predictor._model_30min
        assert "r_squared" in predictor._model_30min


class TestThermalTimeSeriesCollector:
    """Test thermal sample collection and persistence."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory for testing."""
        return tmp_path

    @pytest.fixture
    def collector(self, temp_dir):
        """Create a collector with temp history path."""
        return ThermalTimeSeriesCollector(
            history_path=temp_dir / "thermal_history.jsonl",
            sample_interval_seconds=1,
            enable_vault_logging=False,
        )

    def test_initialization(self, collector):
        """Test collector initialization."""
        assert collector.history_path is not None
        assert collector.history_path.parent.exists()

    def test_record_batch_thermal(self, collector):
        """Test recording batch thermal metrics."""
        collector.record_batch_thermal(
            batch_size=32,
            peak_gpu_temp=80.0,
            throttle_detected=False,
        )

        # Check file was created
        assert collector.history_path.exists()

        # Check content
        with open(collector.history_path) as f:
            line = f.readline()
            data = json.loads(line)
            assert data["batch_size_recent"] == 32
            assert data["gpu_temp_c"] == 80.0
            assert data["throttle_detected"] is False

    def test_record_multiple_thermal_samples(self, collector):
        """Test recording multiple thermal samples."""
        for i in range(10):
            collector.record_batch_thermal(
                batch_size=32 + i,
                peak_gpu_temp=75.0 + i * 0.5,
                throttle_detected=i > 5,
            )

        # Check file
        assert collector.history_path.exists()

        with open(collector.history_path) as f:
            lines = [json.loads(line) for line in f]
            assert len(lines) == 10
            assert lines[0]["gpu_temp_c"] == 75.0
            assert lines[9]["gpu_temp_c"] == 79.5

    @pytest.mark.asyncio
    async def test_load_jsonl_history_async(self, collector):
        """Test async loading of JSONL history."""
        # Record some samples
        for i in range(5):
            collector.record_batch_thermal(
                batch_size=32,
                peak_gpu_temp=75.0 + i * 0.5,
                throttle_detected=False,
            )

        # Load them
        samples = await collector.load_jsonl_history_async(hours=1)
        assert len(samples) >= 5
        assert samples[0]["gpu_temp_c"] == 75.0

    def test_load_jsonl_history_nonexistent(self):
        """Test loading from nonexistent file."""
        samples = load_jsonl_history(Path("/tmp/nonexistent_thermal.jsonl"))
        assert samples == []

    def test_load_jsonl_with_corrupted_lines(self, collector):
        """Test loading JSONL with some corrupted lines."""
        # Write valid JSON with future timestamps (within 7-day window)
        current_time = time.time()
        with open(collector.history_path, "w") as f:
            f.write(f'{{"timestamp": {current_time}, "gpu_temp_c": 75.0}}\n')
            f.write("CORRUPTED DATA\n")
            f.write(f'{{"timestamp": {current_time + 60}, "gpu_temp_c": 76.0}}\n')

        # Should skip corrupted line and load valid ones
        samples = load_jsonl_history(collector.history_path, days=7)
        assert len(samples) == 2
        assert samples[0]["gpu_temp_c"] == 75.0
        assert samples[1]["gpu_temp_c"] == 76.0


class TestBackwardCompatibility:
    """Test backward compatibility and feature flags."""

    def test_predictor_disabled_by_default(self):
        """Test that prediction is opt-in."""
        from cohezion.swarm.dynamic_concurrency_gate import (
            DynamicConcurrencyGate,
        )

        gate = DynamicConcurrencyGate(enable_thermal_prediction=False)
        assert gate.enable_thermal_prediction is False
        assert gate._thermal_predictor is None

    def test_predictor_enabled_optionally(self):
        """Test enabling thermal prediction."""
        from cohezion.swarm.dynamic_concurrency_gate import (
            DynamicConcurrencyGate,
        )

        gate = DynamicConcurrencyGate(enable_thermal_prediction=True)
        assert gate.enable_thermal_prediction is True
        assert gate._thermal_predictor is not None

    def test_singleton_getter(self):
        """Test singleton factory."""
        predictor1 = get_thermal_trend_predictor()
        predictor2 = get_thermal_trend_predictor()
        assert predictor1 is predictor2

    def test_singleton_reset(self):
        """Test singleton reset."""
        predictor1 = get_thermal_trend_predictor()
        predictor2 = get_thermal_trend_predictor(reset=True)
        assert predictor1 is not predictor2

    def test_collector_singleton(self):
        """Test collector singleton."""
        collector1 = get_thermal_time_series_collector()
        collector2 = get_thermal_time_series_collector()
        assert collector1 is collector2


class TestPredictionAccuracy:
    """Test prediction accuracy in realistic scenarios."""

    def test_constant_temperature_prediction(self):
        """Test prediction with constant temperature."""
        predictor = ThermalTrendPredictor()

        # Constant 70°C
        for i in range(20):
            ts = ThermalTimeSeries(
                timestamp=time.time() + i * 60,
                gpu_temp_c=70.0,
                cpu_temp_c=60.0,
                gpu_clock_mhz=2800.0,
                throttle_detected=False,
            )
            predictor.record_sample(ts)

        predicted, _confidence = predictor.predict_temperature_ahead(30)

        # Should predict ~70°C (constant)
        assert 68.0 < predicted < 72.0

    def test_linear_heating_prediction(self):
        """Test prediction with linear heating."""
        predictor = ThermalTrendPredictor()

        # Linear heating: +1°C per minute
        for i in range(30):
            ts = ThermalTimeSeries(
                timestamp=time.time() + i * 60,
                gpu_temp_c=60.0 + i * 1.0,
                cpu_temp_c=50.0,
                gpu_clock_mhz=2800.0,
                throttle_detected=False,
            )
            predictor.record_sample(ts)

        predicted, _confidence = predictor.predict_temperature_ahead(30)

        # Should predict higher temp (30°C increase in 30 min at 1°C/min)
        # But with damping, should be less
        assert predicted > 85.0

    def test_thermal_throttle_warning(self):
        """Test prediction warns of approaching throttle."""
        predictor = ThermalTrendPredictor()

        # Approaching throttle at 92°C
        for i in range(20):
            ts = ThermalTimeSeries(
                timestamp=time.time() + i * 300,
                gpu_temp_c=85.0 + i * 0.3,  # Slowly approaching 92°C
                cpu_temp_c=70.0,
                gpu_clock_mhz=2800.0,
                throttle_detected=i > 10,
            )
            predictor.record_sample(ts)

        predicted, _confidence = predictor.predict_temperature_ahead(30)

        # Should predict high temp
        assert predicted > 87.0


class TestIntegration:
    """Integration tests with concurrency gate."""

    def test_concurrency_gate_with_prediction_enabled(self):
        """Test DynamicConcurrencyGate with prediction enabled."""
        from cohezion.swarm.dynamic_concurrency_gate import (
            DynamicConcurrencyGate,
        )

        gate = DynamicConcurrencyGate(enable_thermal_prediction=True)

        # Should succeed without errors
        concurrency = gate.get_safe_concurrency()
        assert concurrency in [4, 8, 10, 12]

    def test_thermal_collector_integration(self, tmp_path):
        """Test thermal collector integrates with batch executor."""
        collector = ThermalTimeSeriesCollector(
            history_path=tmp_path / "thermal_history.jsonl",
            enable_vault_logging=False,
        )

        # Simulate batch execution
        for i in range(5):
            collector.record_batch_thermal(
                batch_size=16 + i * 4,
                peak_gpu_temp=70.0 + i * 2.0,
                throttle_detected=False,
            )

        # Verify persistence
        samples = load_jsonl_history(tmp_path / "thermal_history.jsonl", days=7)
        assert len(samples) == 5
