"""Item 1013: get_windowed_global_latency_cv(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide coefficient of variation of latency: fleet_stddev / fleet_mean.

Both stddev and mean computed from pooled latencies (NOT avg of per-tool CVs).
0.0 when no recent calls or fleet mean=0. Injectable store. Pure function.

PRIMARY DISC.: tool_a [10,50] + tool_b [90,150]
  pooled [10,50,90,150], n=4, mean=300/4=75
  variance = ((10-75)^2+(50-75)^2+(90-75)^2+(150-75)^2)/4
           = (4225+625+225+5625)/4 = 10700/4 = 2675
  stddev = sqrt(2675) ≈ 51.7205
  CV = 51.7205 / 75 ≈ 0.6896
  (PRIMARY DISC.: kills avg-per-tool-CV; correct pooled-CV≈0.6896).
"""

from __future__ import annotations
import math

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_cv,
    get_windowed_tool_latency_cv,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_cv_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a[10,50] + tool_b[90,150] pooled -> 0.6896.

    Pooled [10,50,90,150] mean=75, variance=2675, stddev≈51.7205.
    CV=51.7205/75≈0.6896.
    Kills avg-per-tool-CV.
    """
    _reset()
    store = _make_store(
        {
            "gcv_a": [(_NOW - 10, float(v), True) for v in [10, 50]],
            "gcv_b": [(_NOW - 10, float(v), True) for v in [90, 150]],
        }
    )
    result = get_windowed_global_latency_cv(_WIN, store=store, now_ms=_NOW)
    lats = [10.0, 50.0, 90.0, 150.0]
    mean = sum(lats) / len(lats)
    variance = sum((lat - mean) ** 2 for lat in lats) / len(lats)
    expected_cv = math.sqrt(variance) / mean
    assert isinstance(result, float)
    assert abs(result - expected_cv) < 1e-9, (
        f"pooled CV={expected_cv:.6f}; kills avg-per-tool; got {result}"
    )


def test_single_tool_matches_per_tool_cv() -> None:
    """With one tool, global CV == per-tool CV."""
    _reset()
    store = _make_store(
        {
            "gcv_one": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
        }
    )
    global_cv = get_windowed_global_latency_cv(_WIN, store=store, now_ms=_NOW)
    per_tool_cv = get_windowed_tool_latency_cv("gcv_one", _WIN, store=store, now_ms=_NOW)
    assert abs(global_cv - per_tool_cv) < 1e-9, (
        f"single tool: global_cv={global_cv} must equal per_tool_cv={per_tool_cv}"
    )


def test_empty_store_returns_zero() -> None:
    _reset()
    assert get_windowed_global_latency_cv(_WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "gcv_old": [(_NOW - _WIN - 100, 100.0, True)] * 5,
        }
    )
    assert get_windowed_global_latency_cv(_WIN, store=store, now_ms=_NOW) == 0.0


def test_all_equal_latencies_cv_is_zero() -> None:
    """All latencies equal across all tools -> CV=0.0."""
    _reset()
    store = _make_store(
        {
            "gcv_zero_a": [(_NOW - 10, 100.0, True)] * 3,
            "gcv_zero_b": [(_NOW - 10, 100.0, True)] * 2,
        }
    )
    result = get_windowed_global_latency_cv(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 0.0) < 1e-9, f"all-equal latencies -> CV=0.0; got {result}"


def test_pooling_differs_from_per_tool_average() -> None:
    """Pooled global CV != simple average of per-tool CVs (when tools have different call volumes).

    This discriminates the pooled implementation from a naive per-tool-averaging implementation.
    tool_a [100] (1 call, CV=0.0) vs tool_b [10, 200, 1000] (3 calls, high CV)
    naive avg = (0.0 + high_cv) / 2
    pooled CV uses all 4 latencies together.
    """
    _reset()
    store = _make_store(
        {
            "gcv_diff_a": [(_NOW - 10, 100.0, True)],  # 1 call, CV would be 0
            "gcv_diff_b": [(_NOW - 10, float(v), True) for v in [10, 200, 1000]],
        }
    )
    global_cv = get_windowed_global_latency_cv(_WIN, store=store, now_ms=_NOW)
    # With only 1 call per-tool-a has CV=0; simple avg would be dominated by tool_b alone
    # Pooled uses all 4 values: [100, 10, 200, 1000] which gives a different CV
    per_b_cv = get_windowed_tool_latency_cv("gcv_diff_b", _WIN, store=store, now_ms=_NOW)
    # global_cv != per_b_cv because the pooled mean is different (100 shifts it)
    assert abs(global_cv - per_b_cv) > 1e-6, (
        f"pooled CV={global_cv} should differ from single-tool-b CV={per_b_cv} "
        f"(tool_a's 100ms call shifts the pooled mean)"
    )


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"gcv_rt": [(_NOW - 10, float(v), True) for v in [50, 100, 200]]})
    assert isinstance(get_windowed_global_latency_cv(_WIN, store=store, now_ms=_NOW), float)
