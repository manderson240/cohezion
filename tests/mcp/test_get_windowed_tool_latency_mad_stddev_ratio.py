"""Item 1033: get_windowed_tool_latency_mad_stddev_ratio(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- MAD/stddev ratio (outlier sensitivity index).

ratio = MAD / stddev
0.0 if stddev == 0 (guard). Injectable store. Pure function.

For a perfect normal distribution: ratio ≈ 0.7979 (= 1/sqrt(2/π)).
Values near 0 → stddev is outlier-dominated (MAD insensitive, stddev inflated).
Values near 1 → uniform-ish data, both measures agree.

PRIMARY DISC.: lats [10, 10, 10, 10, 100]
  median = 10.0 (4 of 5 values are 10)
  sorted_devs = [0, 0, 0, 0, 90], MAD = 0.0
  stddev = 36.0
  ratio = 0.0 / 36.0 = 0.0
  (PRIMARY DISC.: kills MAD=0 standalone; kills stddev=36 standalone;
   kills ratio=1.0; correct ratio=0.0 showing outlier-dominated stddev).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_mad_stddev_ratio,
    get_windowed_tool_latency_mad_ms,
    get_windowed_tool_latency_stddev_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_mad_stddev_ratio_primary_discriminator() -> None:
    """PRIMARY DISC.: [10,10,10,10,100] -> ratio=0.0.

    median=10 -> MAD=0.0 (4/5 calls at median, outlier doesn't move MAD).
    stddev=36.0 (inflated by outlier).
    ratio = 0/36 = 0.0 (stddev is entirely outlier-driven, MAD is not).
    Kills ratio=36 (stddev standalone); kills ratio=1.0 (wrong).
    """
    _reset()
    store = _make_store({
        "msr_a": [(_NOW - 10, float(v), True) for v in [10, 10, 10, 10, 100]],
    })
    result = get_windowed_tool_latency_mad_stddev_ratio("msr_a", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert result == 0.0, f"MAD=0, stddev=36 -> ratio=0.0; got {result}"


def test_ratio_equals_mad_over_stddev() -> None:
    """ratio == MAD / stddev (arithmetic identity)."""
    _reset()
    lats = [50.0, 100.0, 150.0, 200.0, 250.0]
    store = _make_store({
        "msr_id": [(_NOW - 10, v, True) for v in lats],
    })
    ratio = get_windowed_tool_latency_mad_stddev_ratio("msr_id", _WIN, store=store, now_ms=_NOW)
    mad = get_windowed_tool_latency_mad_ms("msr_id", _WIN, store=store, now_ms=_NOW)
    stddev = get_windowed_tool_latency_stddev_ms("msr_id", _WIN, store=store, now_ms=_NOW)
    if stddev > 0:
        assert abs(ratio - mad / stddev) < 1e-9, f"ratio={ratio} != MAD/stddev={mad}/{stddev}={mad/stddev}"


def test_all_equal_stddev_zero_returns_zero() -> None:
    """stddev=0 -> ratio=0.0 (guard, not division-by-zero)."""
    _reset()
    store = _make_store({
        "msr_eq": [(_NOW - 10, 100.0, True)] * 5,
    })
    result = get_windowed_tool_latency_mad_stddev_ratio("msr_eq", _WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"stddev=0 -> ratio=0.0 (guard); got {result}"


def test_ratio_in_zero_to_one_range() -> None:
    """MAD/stddev is always in [0, 1] for any distribution (MAD <= stddev always)."""
    _reset()
    store = _make_store({
        "msr_rng": [(_NOW - 10, float(v), True) for v in [10, 30, 50, 70, 90, 200]],
    })
    result = get_windowed_tool_latency_mad_stddev_ratio("msr_rng", _WIN, store=store, now_ms=_NOW)
    assert 0.0 <= result <= 1.0 + 1e-9, f"ratio must be in [0,1]; got {result}"


def test_uniform_distribution_high_ratio() -> None:
    """Uniform-ish data (no outliers) -> ratio close to normal's 0.7979."""
    _reset()
    # Uniform [10..100], no outliers -> MAD/stddev near 0.79
    lats = [float(x) for x in range(10, 101, 10)]  # [10,20,...,100]
    store = _make_store({
        "msr_uni": [(_NOW - 10, v, True) for v in lats],
    })
    result = get_windowed_tool_latency_mad_stddev_ratio("msr_uni", _WIN, store=store, now_ms=_NOW)
    assert result > 0.5, f"uniform data -> ratio>0.5; got {result}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_latency_mad_stddev_ratio("no_such_msr", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "msr_old": [(_NOW - _WIN - 100, 100.0, True)] * 5,
    })
    assert get_windowed_tool_latency_mad_stddev_ratio("msr_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"msr_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 200]]})
    assert isinstance(
        get_windowed_tool_latency_mad_stddev_ratio("msr_rt", _WIN, store=store, now_ms=_NOW), float
    )
