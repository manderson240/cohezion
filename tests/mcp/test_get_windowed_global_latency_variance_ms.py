"""Item 1002: get_windowed_global_latency_variance_ms(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide population variance of pooled latency in window.

Fleet-wide dual of get_windowed_tool_latency_variance_ms (item 1001).
Pools ALL recent latencies from all tools then computes population variance.
0.0 for <2 pooled calls. Returns float.

PRIMARY DISC.:
  tool_a [10, 30] + tool_b [20, 40] -> pooled [10, 20, 30, 40]
  mean = (10+20+30+40)/4 = 25.0
  pop_var = ((10-25)^2+(20-25)^2+(30-25)^2+(40-25)^2)/4 = (225+25+25+225)/4 = 500/4 = 125.0

  per-tool variances:
    tool_a [10,30]: mean=20, var=((10-20)^2+(30-20)^2)/2=100.0
    tool_b [20,40]: mean=30, var=((20-30)^2+(40-30)^2)/2=100.0
    avg-of-per-tool-var = (100+100)/2 = 100.0  -> WRONG
    pooled var = 125.0                          -> CORRECT (different)

Kills: avg-of-per-tool-variance=100.0.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_variance_ms,
    get_windowed_tool_latency_variance_ms,
    get_windowed_global_latency_stddev_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_pooled_variance_not_avg_per_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: pooled var=125.0 != avg-of-per-tool-var=100.0.

    tool_a [10,30]: var=100.0
    tool_b [20,40]: var=100.0
    avg-of-per-tool = 100.0  -> WRONG
    pooled [10,20,30,40]: mean=25.0, var=125.0  -> CORRECT
    """
    _reset()
    store = _make_store({
        "gv_a": [(_NOW - 10, 10.0, True), (_NOW - 10, 30.0, True)],
        "gv_b": [(_NOW - 10, 20.0, True), (_NOW - 10, 40.0, True)],
    })
    result = get_windowed_global_latency_variance_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 125.0) < 1e-9, (
        f"pooled var=125.0; kills avg-per-tool=100.0; got {result}"
    )
    # not avg-of-per-tool
    assert abs(result - 100.0) > 1.0


def test_variance_equals_stddev_squared() -> None:
    """Fleet variance == fleet stddev^2 (population, from item 984)."""
    _reset()
    store = _make_store({
        "gv_sq_a": [(_NOW - 10, float(v), True) for v in [10, 20, 30]],
        "gv_sq_b": [(_NOW - 10, float(v), True) for v in [40, 50, 60]],
    })
    var = get_windowed_global_latency_variance_ms(_WIN, store=store, now_ms=_NOW)
    std = get_windowed_global_latency_stddev_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(var - std ** 2) < 1e-6, (
        f"global_var={var} must equal global_std^2={std**2}"
    )


def test_single_tool_matches_per_tool_variance() -> None:
    """With one tool, global variance == per-tool variance."""
    _reset()
    store = _make_store({
        "gv_one": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40]],
    })
    global_var = get_windowed_global_latency_variance_ms(_WIN, store=store, now_ms=_NOW)
    per_tool = get_windowed_tool_latency_variance_ms("gv_one", _WIN, store=store, now_ms=_NOW)
    assert abs(global_var - per_tool) < 1e-9, (
        f"single tool: global_var={global_var} must equal per_tool_var={per_tool}"
    )


def test_empty_store_returns_zero() -> None:
    _reset()
    assert get_windowed_global_latency_variance_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_old_calls_excluded() -> None:
    """Old calls outside window must not contribute to variance."""
    _reset()
    store = _make_store({
        "gv_old": [(_NOW - _WIN - 100, 9999.0, True)] * 5
        + [(_NOW - 10, float(v), True) for v in [10, 20, 30]],
    })
    result = get_windowed_global_latency_variance_ms(_WIN, store=store, now_ms=_NOW)
    # [10,20,30]: mean=20, var=200/3≈66.67
    assert abs(result - 200.0 / 3.0) < 1e-6, (
        f"Old excluded; var([10,20,30])=200/3≈66.67; got {result}"
    )


def test_non_negative() -> None:
    """Variance is always non-negative."""
    _reset()
    store = _make_store({
        "gv_nn": [(_NOW - 10, float(v), True) for v in range(1, 11)],
    })
    result = get_windowed_global_latency_variance_ms(_WIN, store=store, now_ms=_NOW)
    assert result >= 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"gv_rt": [(_NOW - 10, float(v), True) for v in [10, 20, 30]]})
    assert isinstance(get_windowed_global_latency_variance_ms(_WIN, store=store, now_ms=_NOW), float)
