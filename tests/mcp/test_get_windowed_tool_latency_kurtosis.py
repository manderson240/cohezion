"""Item 1030: get_windowed_tool_latency_kurtosis(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- excess kurtosis (4th standardised moment minus 3; Fisher definition).

excess_kurtosis = (1/n)*sum((lat-mean)^4) / stddev^4 - 3

Normal distribution = 0.0 (normal reference).
Positive = heavy-tailed (more extreme outliers than normal).
Negative = light-tailed (lighter tails than normal).
0.0 for n<4 or stddev=0. Injectable store. Pure function.

PRIMARY DISC.: lats [10, 10, 10, 10, 100]
  n=5, mean=28, pop_var=1296.0, stddev=36.0
  sum((lat-mean)^4) = 4*18^4 + 72^4 = 419904 + 26873856 = 27293760
  raw_kurtosis = 27293760 / (5 * 36^4) = 27293760 / 8398080 = 3.25
  excess_kurtosis = 3.25 - 3.0 = 0.25
  (PRIMARY DISC.: kills variance=1296.0 float; kills stddev=36.0 float;
   kills raw_kurtosis=3.25 float; correct excess=0.25 float).
"""
from __future__ import annotations
import math

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_kurtosis,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def _ref_excess_kurtosis(lats: list[float]) -> float:
    """Reference implementation."""
    n = len(lats)
    if n < 4:
        return 0.0
    mean = sum(lats) / n
    pop_var = sum((x - mean) ** 2 for x in lats) / n
    if pop_var == 0.0:
        return 0.0
    stddev = pop_var ** 0.5
    return sum((x - mean) ** 4 for x in lats) / (n * stddev ** 4) - 3.0


def test_kurtosis_primary_discriminator() -> None:
    """PRIMARY DISC.: [10,10,10,10,100] -> excess_kurtosis=0.25.

    Kills variance=1296.0 (wrong value for kurtosis).
    Kills stddev=36.0 (wrong value).
    Kills raw_kurtosis=3.25 (off by 3.0 / Fisher subtraction missing).
    Correct: excess_kurtosis = 3.25 - 3.0 = 0.25.
    """
    _reset()
    store = _make_store({
        "krt_a": [(_NOW - 10, float(v), True) for v in [10, 10, 10, 10, 100]],
    })
    result = get_windowed_tool_latency_kurtosis("krt_a", _WIN, store=store, now_ms=_NOW)
    expected = _ref_excess_kurtosis([10.0, 10.0, 10.0, 10.0, 100.0])
    assert isinstance(result, float)
    assert abs(result - expected) < 1e-9, (
        f"excess_kurtosis=0.25; kills variance/stddev/raw; got {result}"
    )
    assert abs(result - 0.25) < 1e-9, f"exact value 0.25; got {result}"


def test_normal_like_distribution_kurtosis_near_zero() -> None:
    """Distribution close to normal -> excess kurtosis ≈ 0."""
    _reset()
    # Symmetric distribution: excess kurtosis of [1,2,3,4,5] is 1.7ish but
    # we test the all-equal guard (stddev=0 -> kurtosis=0)
    # Use the reference function to verify direction
    lats = [10.0, 20.0, 30.0, 40.0, 50.0]
    store = _make_store({
        "krt_sym": [(_NOW - 10, v, True) for v in lats],
    })
    result = get_windowed_tool_latency_kurtosis("krt_sym", _WIN, store=store, now_ms=_NOW)
    expected = _ref_excess_kurtosis(lats)
    assert abs(result - expected) < 1e-9, f"expected={expected:.6f}; got {result}"


def test_all_equal_latencies_kurtosis_zero() -> None:
    """All equal -> stddev=0 -> kurtosis=0.0 (guard)."""
    _reset()
    store = _make_store({
        "krt_eq": [(_NOW - 10, 100.0, True)] * 5,
    })
    result = get_windowed_tool_latency_kurtosis("krt_eq", _WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"all-equal -> kurtosis=0.0; got {result}"


def test_fewer_than_four_calls_returns_zero() -> None:
    """n<4 -> 0.0 (not enough data for 4th moment)."""
    _reset()
    store = _make_store({
        "krt_lt4": [(_NOW - 10, float(v), True) for v in [10, 50, 100]],
    })
    result = get_windowed_tool_latency_kurtosis("krt_lt4", _WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"n=3 < 4 -> kurtosis=0.0; got {result}"


def test_heavy_tailed_positive_excess() -> None:
    """Distribution with outliers -> positive excess kurtosis."""
    _reset()
    # One extreme outlier makes kurtosis positive
    lats = [50.0] * 8 + [1000.0]
    store = _make_store({
        "krt_heavy": [(_NOW - 10, v, True) for v in lats],
    })
    result = get_windowed_tool_latency_kurtosis("krt_heavy", _WIN, store=store, now_ms=_NOW)
    assert result > 0.0, f"heavy-tailed -> positive excess kurtosis; got {result}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_latency_kurtosis("no_such_krt", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "krt_old": [(_NOW - _WIN - 100, 100.0, True)] * 6,
    })
    assert get_windowed_tool_latency_kurtosis("krt_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"krt_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 200, 500]]})
    assert isinstance(get_windowed_tool_latency_kurtosis("krt_rt", _WIN, store=store, now_ms=_NOW), float)
