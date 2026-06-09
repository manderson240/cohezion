"""Item 1013: get_windowed_global_latency_cv() — fleet-wide coefficient of variation.

get_windowed_global_latency_cv(window_ms, *, store=None, now_ms=None) -> float

CV = fleet_stddev_ms / fleet_mean_ms — both from POOLED latencies, NOT average-of-per-tool-CVs.
0.0 when no recent calls or fleet mean=0.

Discriminating tests:
  1. PRIMARY DISC.: tool_a[10,50] + tool_b[90,150] -> pooled_CV≈0.6896
       per-tool CVs: cv_a=0.6667, cv_b=0.25
       avg-per-tool-CV = (0.6667+0.25)/2 = 0.4583         (WRONG)
       pooled: mean=75, stddev≈51.720, CV≈0.6896           (CORRECT)
  2. Consistent with fleet_stddev / fleet_mean.
  3. Empty store -> 0.0.
  4. Old calls excluded.
  5. Returns float.
"""
from __future__ import annotations

import math
import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_global_latency_cv,
)

NOW_MS = 100_000.0
WINDOW_MS = 10_000.0


@pytest.fixture(autouse=True)
def _clean():
    _WINDOWED_TELEMETRY.clear()
    yield
    _WINDOWED_TELEMETRY.clear()


def _add(store: dict, tool: str, lat: float, ts: float, ok: bool = True) -> None:
    store.setdefault(tool, []).append((ts, lat, ok))


def _recent() -> float:
    return NOW_MS - 5_000.0


def _old() -> float:
    return NOW_MS - WINDOW_MS - 1_000.0


def test_pooled_not_avg_per_tool_cv_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a[10,50] + tool_b[90,150] -> pooled_CV≈0.6896.

    per-tool CVs (wrong approach):
      tool_a [10, 50]: mean=30, var=400, stddev=20, CV=0.6667
      tool_b [90, 150]: mean=120, var=900, stddev=30, CV=0.25
      avg-per-tool-CV = (0.6667 + 0.25) / 2 = 0.4583   (WRONG)

    pooled [10, 50, 90, 150] (CORRECT):
      mean=75, var=2675, stddev≈51.720, CV≈0.6896

    Kills any impl averaging per-tool CVs instead of pooling.
    """
    store: dict = {}
    ts = _recent()
    for lat in [10.0, 50.0]:
        _add(store, "gcv_a", lat, ts)
    for lat in [90.0, 150.0]:
        _add(store, "gcv_b", lat, ts)

    result = get_windowed_global_latency_cv(WINDOW_MS, store=store, now_ms=NOW_MS)

    # pooled: mean=75, var=2675, stddev≈51.72, CV≈0.6896
    pooled_lats = [10.0, 50.0, 90.0, 150.0]
    mean = sum(pooled_lats) / len(pooled_lats)
    var = sum((x - mean) ** 2 for x in pooled_lats) / len(pooled_lats)
    expected_cv = math.sqrt(var) / mean

    assert isinstance(result, float)
    assert abs(result - expected_cv) < 1e-9, (
        f"pooled_CV={expected_cv:.6f}; kills avg-per-tool-CV=0.4583; got {result}"
    )
    # Confirm the wrong answer is distinct
    avg_per_tool_cv = (20.0 / 30.0 + 30.0 / 120.0) / 2
    assert abs(result - avg_per_tool_cv) > 0.1, "Fixture degenerate: pooled == avg-per-tool"


def test_empty_store_returns_zero() -> None:
    result = get_windowed_global_latency_cv(WINDOW_MS, store={}, now_ms=NOW_MS)
    assert isinstance(result, float)
    assert result == 0.0


def test_old_calls_excluded() -> None:
    """Old high-variance calls must not inflate the fleet CV."""
    store: dict = {}
    for lat in [1.0, 9999.0]:
        _add(store, "gcv_old", lat, _old())
    # Recent uniform calls: CV=0
    for _ in range(4):
        _add(store, "gcv_old", 100.0, _recent())

    result = get_windowed_global_latency_cv(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert result == 0.0, f"Old excluded; recent uniform -> CV=0.0; got {result}"


def test_uniform_lats_returns_zero() -> None:
    """All same latency: stddev=0 -> CV=0.0."""
    store: dict = {}
    for tool in ["gcv_u1", "gcv_u2"]:
        for _ in range(3):
            _add(store, tool, 100.0, _recent())

    result = get_windowed_global_latency_cv(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 0.0, f"Uniform latency: CV=0.0; got {result}"


def test_returns_float() -> None:
    store: dict = {}
    for lat in [10.0, 20.0, 30.0, 40.0, 50.0]:
        _add(store, "gcv_rt", lat, _recent())
    result = get_windowed_global_latency_cv(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float), f"Must return float; got {type(result)}"
