"""Item 1042: get_windowed_global_latency_mad_stddev_ratio(window_ms, *, store=None, now_ms=None) -> float
-- Fleet-wide MAD/stddev ratio (outlier sensitivity index).

ratio = pooled_MAD / pooled_stddev
0.0 if pooled_stddev == 0. Injectable store. Pure function.
Fleet dual of item 1033. Composes fleet MAD (item 1037) and fleet stddev.

PRIMARY DISC.: tool_a=[10,10,10,10] + tool_b=[100]
  pooled=[10,10,10,10,100] n=5
  median=10, sorted_devs=[0,0,0,0,90], MAD=0.0
  stddev=36.0
  ratio = 0.0 / 36.0 = 0.0
  (PRIMARY DISC.: kills ratio=1.0 (wrong);
   kills stddev=36.0 (standalone, not ratio);
   correct ratio=0.0 — stddev inflated by outlier, MAD insensitive).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_mad_stddev_ratio,
    get_windowed_global_latency_mad_ms,
    get_windowed_global_latency_stddev_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_mad_stddev_ratio_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a=[10,10,10,10]+tool_b=[100] -> ratio=0.0.

    pooled median=10, MAD=0.0 (all devs from the 4 tens are 0).
    stddev=36.0 (inflated by outlier 100).
    ratio=0.0/36.0=0.0 — stddev is entirely outlier-driven, MAD is not.
    Kills ratio=1.0; kills stddev=36.0 standalone.
    """
    _reset()
    store = _make_store(
        {
            "gmsr_a": [(_NOW - 10, 10.0, True)] * 4,
            "gmsr_b": [(_NOW - 10, 100.0, True)],
        }
    )
    result = get_windowed_global_latency_mad_stddev_ratio(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert result == 0.0, f"MAD=0, stddev=36 -> ratio=0.0; got {result}"


def test_ratio_equals_mad_over_stddev() -> None:
    """ratio == pooled_MAD / pooled_stddev (arithmetic identity)."""
    _reset()
    lats = [50.0, 100.0, 150.0, 200.0, 250.0]
    store = _make_store(
        {
            "gmsr_id": [(_NOW - 10, v, True) for v in lats],
        }
    )
    ratio = get_windowed_global_latency_mad_stddev_ratio(_WIN, store=store, now_ms=_NOW)
    mad = get_windowed_global_latency_mad_ms(_WIN, store=store, now_ms=_NOW)
    stddev = get_windowed_global_latency_stddev_ms(_WIN, store=store, now_ms=_NOW)
    if stddev > 0:
        assert abs(ratio - mad / stddev) < 1e-9, (
            f"ratio={ratio} != MAD/stddev={mad}/{stddev}={mad / stddev}"
        )


def test_all_equal_stddev_zero_returns_zero() -> None:
    """All equal pooled latencies -> stddev=0 -> ratio=0.0 (guard)."""
    _reset()
    store = _make_store(
        {
            "gmsr_eq": [(_NOW - 10, 100.0, True)] * 8,
        }
    )
    result = get_windowed_global_latency_mad_stddev_ratio(_WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"stddev=0 -> ratio=0.0; got {result}"


def test_ratio_in_zero_to_one_range() -> None:
    """MAD/stddev is always in [0, 1] (MAD ≤ stddev always)."""
    _reset()
    store = _make_store(
        {
            "gmsr_rng": [(_NOW - 10, float(v), True) for v in [10, 30, 50, 70, 90, 200]],
        }
    )
    result = get_windowed_global_latency_mad_stddev_ratio(_WIN, store=store, now_ms=_NOW)
    assert 0.0 <= result <= 1.0 + 1e-9, f"ratio must be in [0,1]; got {result}"


def test_uniform_distribution_high_ratio() -> None:
    """Uniform-ish data (no outliers) -> ratio close to normal's 0.7979."""
    _reset()
    store = _make_store(
        {
            "gmsr_uni": [(_NOW - 10, float(x), True) for x in range(10, 101, 10)],
        }
    )
    result = get_windowed_global_latency_mad_stddev_ratio(_WIN, store=store, now_ms=_NOW)
    assert result > 0.5, f"uniform data -> ratio>0.5; got {result}"


def test_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_global_latency_mad_stddev_ratio(_WIN, store={}, now_ms=_NOW) == 0.0


def test_all_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "gmsr_old": [(_NOW - _WIN - 100, 100.0, True)] * 5,
        }
    )
    assert get_windowed_global_latency_mad_stddev_ratio(_WIN, store=store, now_ms=_NOW) == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"gmsr_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 200]]})
    assert isinstance(
        get_windowed_global_latency_mad_stddev_ratio(_WIN, store=store, now_ms=_NOW), float
    )
