"""Item 1001: get_windowed_tool_latency_variance_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- per-tool population variance of latency in window.

Population variance (divide by n, not n-1).
Complements get_windowed_tool_latency_stddev_ms (item 983): variance = stddev^2.
0.0 for unknown tools or <2 calls. Returns float.

PRIMARY DISC.: lats [10, 20, 30] -> variance=66.67 (not sample_var=100.0, not stddev≈8.165)
  mean = (10+20+30)/3 = 20.0
  var  = ((10-20)^2 + (20-20)^2 + (30-20)^2) / 3 = (100+0+100)/3 = 200/3 ≈ 66.67
  sample_var = 200/2 = 100.0  (divide by n-1=2 -> WRONG)
  stddev = sqrt(200/3) ≈ 8.165 (sqrt of variance -> WRONG; this is the un-rooted version)
"""
from __future__ import annotations

import math

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_variance_ms,
    get_windowed_tool_latency_stddev_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_variance_primary_discriminator() -> None:
    """FALSIFIABLE: [10,20,30] -> variance=200/3≈66.67 (not sample_var=100, not stddev≈8.165).

    Kills impl dividing by n-1 (sample variance = 100.0).
    Kills impl returning stddev (sqrt(66.67)≈8.165).
    """
    _reset()
    store = _make_store({
        "var_a": [(_NOW - 10, float(v), True) for v in [10, 20, 30]],
    })
    result = get_windowed_tool_latency_variance_ms("var_a", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    expected = 200.0 / 3.0  # population variance
    assert abs(result - expected) < 1e-6, (
        f"pop_var([10,20,30])=200/3≈66.67; kills sample=100.0 or stddev≈8.165; got {result}"
    )
    # not sample variance (n-1)
    assert abs(result - 100.0) > 1.0
    # not stddev
    assert abs(result - math.sqrt(expected)) > 1.0


def test_variance_equals_stddev_squared() -> None:
    """variance == stddev^2 (population stddev from item 983)."""
    _reset()
    store = _make_store({
        "var_sq": [(_NOW - 10, float(v), True) for v in [5, 15, 25, 35, 45]],
    })
    var = get_windowed_tool_latency_variance_ms("var_sq", _WIN, store=store, now_ms=_NOW)
    std = get_windowed_tool_latency_stddev_ms("var_sq", _WIN, store=store, now_ms=_NOW)
    assert abs(var - std ** 2) < 1e-6, (
        f"variance={var} must equal stddev^2={std**2}"
    )


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_latency_variance_ms("no_such_var", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "var_old": [(_NOW - _WIN - 100, 50.0, True)] * 5,
    })
    assert get_windowed_tool_latency_variance_ms("var_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_single_call_returns_zero() -> None:
    """Single observation -> variance=0.0 (population variance needs >=2)."""
    _reset()
    store = _make_store({"var_one": [(_NOW - 10, 42.0, True)]})
    assert get_windowed_tool_latency_variance_ms("var_one", _WIN, store=store, now_ms=_NOW) == 0.0


def test_uniform_distribution_variance_zero() -> None:
    """All equal latencies -> variance=0.0."""
    _reset()
    store = _make_store({
        "var_unif": [(_NOW - 10, 20.0, True)] * 6,
    })
    result = get_windowed_tool_latency_variance_ms("var_unif", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 0.0) < 1e-9, f"Uniform lats -> variance=0.0; got {result}"


def test_non_negative() -> None:
    """Variance is always non-negative."""
    _reset()
    store = _make_store({
        "var_nn": [(_NOW - 10, float(v), True) for v in range(1, 11)],
    })
    result = get_windowed_tool_latency_variance_ms("var_nn", _WIN, store=store, now_ms=_NOW)
    assert result >= 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"var_rtype": [(_NOW - 10, float(v), True) for v in [10, 20, 30]]})
    assert isinstance(get_windowed_tool_latency_variance_ms("var_rtype", _WIN, store=store, now_ms=_NOW), float)
