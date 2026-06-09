"""Item 1022: get_windowed_tool_latency_skewness(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- per-tool latency skewness (3rd standardised moment).

population_skewness = mean(((lat - mean) / stddev)^3)
                    = (1/n) * sum((lat - mean)^3) / stddev^3

0.0 for <3 calls or stddev=0 (symmetric/single-value distribution).
Injectable store. Pure function.
Positive skew -> right tail (slow outliers); negative skew -> left tail (fast outliers).

PRIMARY DISC.: lats [10, 10, 10, 100]
  n=4, mean=(130/4)=32.5
  deviations: [10-32.5, 10-32.5, 10-32.5, 100-32.5] = [-22.5, -22.5, -22.5, 67.5]
  pop_variance = (3*22.5^2 + 67.5^2)/4 = (1518.75+4556.25)/4 = 6075/4 = 1518.75
  pop_stddev = sqrt(1518.75) ≈ 38.9712
  skewness = (3*(-22.5)^3 + 67.5^3) / (4 * 38.9712^3)
           = (3*(-11390.625) + 307546.875) / (4 * 59153.87...)
           = (-34171.875 + 307546.875) / 236615.5...
           = 273375.0 / 236615.5...
           ≈ 1.1554 (positive skew, heavy right tail from the 100ms outlier)
  PRIMARY DISC.: kills stddev≈38.97; kills variance≈1518.75; correct skewness≈1.1554.
"""
from __future__ import annotations
import math

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_skewness,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def _pop_skewness(lats: list[float]) -> float:
    """Reference implementation for tests."""
    n = len(lats)
    if n < 3:
        return 0.0
    mean = sum(lats) / n
    pop_variance = sum((lat - mean) ** 2 for lat in lats) / n
    if pop_variance == 0.0:
        return 0.0
    pop_stddev = math.sqrt(pop_variance)
    return sum((lat - mean) ** 3 for lat in lats) / (n * pop_stddev ** 3)


def test_skewness_primary_discriminator() -> None:
    """PRIMARY DISC.: [10,10,10,100] -> skewness≈1.1554 (positive right tail).

    Kills stddev≈38.97 (wrong value).
    Kills variance≈1518.75 (wrong value).
    Kills count=4 (int, wrong type).
    """
    _reset()
    store = _make_store({
        "sk_a": [(_NOW - 10, float(v), True) for v in [10, 10, 10, 100]],
    })
    result = get_windowed_tool_latency_skewness("sk_a", _WIN, store=store, now_ms=_NOW)
    expected = _pop_skewness([10.0, 10.0, 10.0, 100.0])
    assert isinstance(result, float)
    assert abs(result - expected) < 1e-9, (
        f"skewness≈{expected:.6f} (right-tail outlier); kills stddev/variance; got {result}"
    )


def test_symmetric_distribution_skewness_near_zero() -> None:
    """Symmetric distribution -> skewness ≈ 0."""
    _reset()
    store = _make_store({
        "sk_sym": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
    })
    result = get_windowed_tool_latency_skewness("sk_sym", _WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"symmetric [10,20,30,40,50] -> skewness≈0; got {result}"


def test_left_skewed_distribution_negative() -> None:
    """Left tail (fast outlier) -> negative skewness."""
    _reset()
    store = _make_store({
        "sk_left": [(_NOW - 10, float(v), True) for v in [1, 90, 90, 90]],
    })
    result = get_windowed_tool_latency_skewness("sk_left", _WIN, store=store, now_ms=_NOW)
    expected = _pop_skewness([1.0, 90.0, 90.0, 90.0])
    assert result < 0.0, f"left-tail outlier -> negative skew; got {result}"
    assert abs(result - expected) < 1e-9, f"expected={expected}; got {result}"


def test_all_equal_latencies_skewness_zero() -> None:
    """All latencies equal -> stddev=0 -> skewness=0.0 (guard)."""
    _reset()
    store = _make_store({
        "sk_zero": [(_NOW - 10, 100.0, True)] * 5,
    })
    result = get_windowed_tool_latency_skewness("sk_zero", _WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"all-equal -> skewness=0.0; got {result}"


def test_fewer_than_three_calls_returns_zero() -> None:
    """<3 calls -> 0.0 (not enough data for meaningful skewness)."""
    _reset()
    store = _make_store({
        "sk_lt3": [(_NOW - 10, 10.0, True), (_NOW - 20, 100.0, True)],
    })
    result = get_windowed_tool_latency_skewness("sk_lt3", _WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"2 calls -> 0.0; got {result}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_latency_skewness("no_such_sk", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "sk_old": [(_NOW - _WIN - 100, 100.0, True)] * 5,
    })
    assert get_windowed_tool_latency_skewness("sk_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"sk_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 200]]})
    assert isinstance(
        get_windowed_tool_latency_skewness("sk_rt", _WIN, store=store, now_ms=_NOW), float
    )
