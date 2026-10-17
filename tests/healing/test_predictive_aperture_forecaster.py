"""Unit tests for PredictiveApertureForecaster (Strix Halo UMA telemetry forecasting)."""

from __future__ import annotations

import pytest
from cohezion.healing.drift_analyzer import PredictiveApertureForecaster


def test_predictive_aperture_insufficient_data() -> None:
    forecaster = PredictiveApertureForecaster()
    res = forecaster.forecast_trajectory(horizon_minutes=15.0)
    assert res["status"] == "INSUFFICIENT_DATA"
    assert res["velocity_gb_per_min"] == 0.0

    forecaster.record_observation(timestamp_sec=100.0, used_gb=50.0, swap_used_gb=0.1)
    res_one = forecaster.forecast_trajectory(horizon_minutes=15.0)
    assert res_one["status"] == "INSUFFICIENT_DATA"
    assert res_one["current_gb"] == 50.0


def test_predictive_aperture_nominal_stability() -> None:
    forecaster = PredictiveApertureForecaster(
        max_aperture_gb=120.0,
        warning_threshold_gb=110.0,
        critical_threshold_gb=115.0,
    )
    # Record flat usage: 60GB over 10 minutes
    for minute in range(10):
        forecaster.record_observation(
            timestamp_sec=minute * 60.0,
            used_gb=60.0 + (minute % 2) * 0.1,
            swap_used_gb=0.2,
        )

    res = forecaster.forecast_trajectory(horizon_minutes=15.0)
    assert res["status"] == "NOMINAL_STABLE"
    assert abs(res["velocity_gb_per_min"]) < 0.05
    assert res["projected_gb"] < 65.0
    assert res["recommendation"] == "MAINTAIN_CURRENT_CADENCE"


def test_predictive_aperture_critical_spike_detection() -> None:
    forecaster = PredictiveApertureForecaster(
        max_aperture_gb=120.0,
        warning_threshold_gb=110.0,
        critical_threshold_gb=115.0,
    )
    # Rapid memory consumption: rising from 90GB to 110GB in 10 minutes (2.0 GB/min)
    for minute in range(11):
        forecaster.record_observation(
            timestamp_sec=minute * 60.0,
            used_gb=90.0 + minute * 2.0,
            swap_used_gb=0.5,
        )

    # At minute 10, used_gb is 110.0. In 15 minutes at 2.0 GB/min, projected is 140GB (>115GB critical)
    res = forecaster.forecast_trajectory(horizon_minutes=15.0)
    assert res["status"] == "CRITICAL_APERTURE_SPIKE"
    assert res["velocity_gb_per_min"] >= 1.9
    assert res["projected_gb"] > 115.0
    assert res["recommendation"] == "TRIGGER_PROACTIVE_EVICTION_AND_HOTSWAP"
