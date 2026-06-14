"""Item 1020: get_windowed_global_latency_sum_ms(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide sum of all latencies in the window.

Pools ALL tool latencies. 0.0 for empty store. Injectable store. Pure function.
Enables fleet mean: fleet_mean = global_latency_sum / global_call_count.

PRIMARY DISC.: tool_a [10, 50] + tool_b [200, 300] -> 560.0.
  (kills per-tool-sum-a=60; kills per-tool-sum-b=500; correct pooled_sum=560.0 float).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_sum_ms,
    get_windowed_tool_latency_sum_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_latency_sum_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a[10,50] + tool_b[200,300] -> 560.0.

    Kills per-tool-sum-a=60 (only tool_a).
    Kills per-tool-sum-b=500 (only tool_b).
    Correct: 10+50+200+300 = 560.0.
    """
    _reset()
    store = _make_store(
        {
            "gls_a": [(_NOW - 10, float(v), True) for v in [10, 50]],
            "gls_b": [(_NOW - 10, float(v), True) for v in [200, 300]],
        }
    )
    result = get_windowed_global_latency_sum_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 560.0) < 1e-9, f"pooled sum=560.0; kills per-tool=60 or 500; got {result}"


def test_single_tool_matches_per_tool_sum() -> None:
    """With one tool, global sum == per-tool sum."""
    _reset()
    store = _make_store(
        {
            "gls_one": [(_NOW - 10, float(v), True) for v in [10, 50, 200]],
        }
    )
    global_sum = get_windowed_global_latency_sum_ms(_WIN, store=store, now_ms=_NOW)
    per_tool_sum = get_windowed_tool_latency_sum_ms("gls_one", _WIN, store=store, now_ms=_NOW)
    assert abs(global_sum - per_tool_sum) < 1e-9, (
        f"single tool: global_sum={global_sum} must equal per_tool_sum={per_tool_sum}"
    )


def test_sum_equals_mean_times_count() -> None:
    """fleet_sum == fleet_mean * fleet_count (cross-function consistency)."""
    from cohezion.mcp.compound_mcp_telemetry import (
        get_windowed_global_mean_latency_ms,
        get_windowed_global_call_count,
    )

    _reset()
    store = _make_store(
        {
            "gls_cons_a": [(_NOW - 10, float(v), True) for v in [20, 40, 60]],
            "gls_cons_b": [(_NOW - 10, float(v), True) for v in [80, 100]],
        }
    )
    total_sum = get_windowed_global_latency_sum_ms(_WIN, store=store, now_ms=_NOW)
    mean = get_windowed_global_mean_latency_ms(_WIN, store=store, now_ms=_NOW)
    count = get_windowed_global_call_count(_WIN, store=store, now_ms=_NOW)
    assert abs(total_sum - mean * count) < 1e-9, (
        f"sum={total_sum} must equal mean*count={mean}*{count}={mean * count}"
    )


def test_empty_store_returns_zero() -> None:
    _reset()
    assert get_windowed_global_latency_sum_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "gls_old": [(_NOW - _WIN - 100, 999.0, True)] * 5,
        }
    )
    assert get_windowed_global_latency_sum_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"gls_rt": [(_NOW - 10, float(v), True) for v in [50, 100, 200]]})
    assert isinstance(get_windowed_global_latency_sum_ms(_WIN, store=store, now_ms=_NOW), float)
