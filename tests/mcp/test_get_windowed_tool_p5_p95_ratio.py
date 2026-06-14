"""Item 1045: get_windowed_tool_p5_p95_ratio(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- p5/p95 tail symmetry index (wider than p10/p90).

Thin composition: p5 / p95; 0.0 if p95 == 0.0.
Injectable store. Pure function.

PRIMARY DISC.: lats [10,20,30,40,50,60,70,80,90,100] n=10
  p5  = idx=0.45 -> 10 + 0.45*10 = 14.5
  p95 = idx=8.55 -> 90 + 0.55*10 = 95.5
  ratio = 14.5 / 95.5 ≈ 0.15183...
  (PRIMARY DISC.: kills p10/p90 ratio (p10=19.0, p90=91.0, ratio≈0.2088 -- different percentiles);
   kills ratio=1.0 (symmetric assumption);
   correct ratio=14.5/95.5≈0.15183 via linear interpolation).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_p5_p95_ratio,
    get_windowed_tool_p5_ms,
    get_windowed_latency_percentile,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_p5_p95_ratio_primary_discriminator() -> None:
    """PRIMARY DISC.: [10..100] step=10 -> ratio=14.5/95.5≈0.15183.

    Kills p10/p90 ratio (≈0.2088 -- wrong percentile pair).
    Kills ratio=1.0 (symmetric assumption).
    Correct: linear interp p5=14.5, p95=95.5, ratio≈0.15183.
    """
    _reset()
    store = _make_store(
        {
            "p5p95_a": [(_NOW - 10, float(v), True) for v in range(10, 101, 10)],
        }
    )
    result = get_windowed_tool_p5_p95_ratio("p5p95_a", _WIN, store=store, now_ms=_NOW)
    expected = 14.5 / 95.5
    assert isinstance(result, float)
    assert abs(result - expected) < 1e-9, (
        f"ratio=14.5/95.5≈{expected:.6f}; kills p10/p90≈0.2088; got {result}"
    )


def test_ratio_equals_p5_over_p95() -> None:
    """ratio == p5 / p95 (arithmetic identity)."""
    _reset()
    lats = [10.0, 20.0, 50.0, 100.0, 200.0, 500.0]
    store = _make_store(
        {
            "p5p95_id": [(_NOW - 10, v, True) for v in lats],
        }
    )
    ratio = get_windowed_tool_p5_p95_ratio("p5p95_id", _WIN, store=store, now_ms=_NOW)
    p5 = get_windowed_tool_p5_ms("p5p95_id", _WIN, store=store, now_ms=_NOW)
    p95 = get_windowed_latency_percentile("p5p95_id", 95.0, _WIN, store=store, now_ms=_NOW)
    if p95 > 0.0:
        assert abs(ratio - p5 / p95) < 1e-9, f"ratio={ratio} != p5/p95={p5}/{p95}={p5 / p95}"


def test_p5_p95_ratio_less_than_p10_p90_ratio() -> None:
    """p5/p95 <= p10/p90 always (wider tails -> smaller ratio for typical data)."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_tool_p10_p90_ratio

    _reset()
    store = _make_store(
        {
            "p5p95_ord": [(_NOW - 10, float(v), True) for v in range(10, 101, 10)],
        }
    )
    r5_95 = get_windowed_tool_p5_p95_ratio("p5p95_ord", _WIN, store=store, now_ms=_NOW)
    r10_90 = get_windowed_tool_p10_p90_ratio("p5p95_ord", _WIN, store=store, now_ms=_NOW)
    assert r5_95 <= r10_90, (
        f"p5/p95={r5_95:.4f} must be <= p10/p90={r10_90:.4f} (wider tails -> smaller ratio)"
    )


def test_single_call_ratio_zero_division_guard() -> None:
    """Single call -> p95 = that value = p5 -> ratio = 1.0."""
    _reset()
    store = _make_store(
        {
            "p5p95_one": [(_NOW - 10, 75.0, True)],
        }
    )
    result = get_windowed_tool_p5_p95_ratio("p5p95_one", _WIN, store=store, now_ms=_NOW)
    # single value: p5 = p95 = 75.0, ratio = 1.0
    assert abs(result - 1.0) < 1e-9, f"single call -> ratio=1.0; got {result}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_p5_p95_ratio("no_such_p5p95", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "p5p95_old": [(_NOW - _WIN - 100, 100.0, True)] * 5,
        }
    )
    assert get_windowed_tool_p5_p95_ratio("p5p95_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_all_equal_ratio_is_one() -> None:
    """All equal latencies -> p5 = p95 -> ratio = 1.0."""
    _reset()
    store = _make_store(
        {
            "p5p95_eq": [(_NOW - 10, 50.0, True)] * 8,
        }
    )
    result = get_windowed_tool_p5_p95_ratio("p5p95_eq", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"all-equal -> ratio=1.0; got {result}"


def test_ratio_in_zero_to_one_range() -> None:
    """p5/p95 is always in [0, 1] for non-negative latencies."""
    _reset()
    store = _make_store(
        {
            "p5p95_rng": [(_NOW - 10, float(v), True) for v in [10, 30, 50, 70, 90, 200]],
        }
    )
    result = get_windowed_tool_p5_p95_ratio("p5p95_rng", _WIN, store=store, now_ms=_NOW)
    assert 0.0 <= result <= 1.0 + 1e-9, f"ratio must be in [0,1]; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"p5p95_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 200]]})
    assert isinstance(
        get_windowed_tool_p5_p95_ratio("p5p95_rt", _WIN, store=store, now_ms=_NOW), float
    )
