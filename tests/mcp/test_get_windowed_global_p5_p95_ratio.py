"""Item 1047: get_windowed_global_p5_p95_ratio(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide p5/p95 tail symmetry index (pooled raw values).

ratio = global_p5 / global_p95; 0.0 if global_p95 == 0.0.
Fleet dual of per-tool item 1045. Injectable store. Pure function.

PRIMARY DISC.: tool_a=[10,10,10,10] + tool_b=[100]
  pooled=[10,10,10,10,100] n=5
  p5:  idx=0.05*4=0.2 -> 10 + 0.2*(10-10) = 10.0
  p95: idx=0.95*4=3.8 -> 10 + 0.8*(100-10) = 82.0
  ratio = 10.0/82.0 ≈ 0.12195
  (PRIMARY DISC.: kills per-tool-avg:
     tool_a all-equal → ratio=1.0; tool_b single → ratio=1.0; avg=1.0 ≠ 0.12195;
   kills ratio=1.0 (symmetric assumption);
   correct pooled ratio=10.0/82.0≈0.12195).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_p5_p95_ratio,
    get_windowed_global_latency_p5_ms,
    get_windowed_global_latency_percentile,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_p5_p95_ratio_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a=[10,10,10,10]+tool_b=[100] -> pooled ratio≈0.12195.

    Kills per-tool-avg: each tool-ratio=1.0 -> avg=1.0 ≠ 0.12195.
    Kills ratio=1.0 (symmetric assumption).
    Correct: pooled p5=10.0, p95=82.0, ratio≈0.12195.
    """
    _reset()
    store = _make_store(
        {
            "gp5p95_a": [(_NOW - 10, 10.0, True)] * 4,
            "gp5p95_b": [(_NOW - 10, 100.0, True)],
        }
    )
    result = get_windowed_global_p5_p95_ratio(_WIN, store=store, now_ms=_NOW)
    expected = 10.0 / 82.0
    assert isinstance(result, float)
    assert abs(result - expected) < 1e-9, (
        f"pooled ratio=10/82≈{expected:.6f}; kills per-tool-avg=1.0; got {result}"
    )


def test_ratio_equals_p5_over_p95() -> None:
    """ratio == pooled_p5 / pooled_p95 (arithmetic identity)."""
    _reset()
    store = _make_store(
        {
            "gp5p95_id": [(_NOW - 10, float(v), True) for v in [10, 30, 50, 70, 90, 200]],
        }
    )
    ratio = get_windowed_global_p5_p95_ratio(_WIN, store=store, now_ms=_NOW)
    p5 = get_windowed_global_latency_p5_ms(_WIN, store=store, now_ms=_NOW)
    p95 = get_windowed_global_latency_percentile(95.0, _WIN, store=store, now_ms=_NOW)
    if p95 > 0.0:
        assert abs(ratio - p5 / p95) < 1e-9, f"ratio={ratio} != p5/p95={p5}/{p95}={p5 / p95}"


def test_all_equal_ratio_is_one() -> None:
    """All equal latencies -> p5 = p95 -> ratio = 1.0."""
    _reset()
    store = _make_store(
        {
            "gp5p95_eq": [(_NOW - 10, 60.0, True)] * 8,
        }
    )
    result = get_windowed_global_p5_p95_ratio(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"all-equal -> ratio=1.0; got {result}"


def test_ratio_in_zero_to_one_range() -> None:
    """p5/p95 is always in [0, 1] for non-negative latencies."""
    _reset()
    store = _make_store(
        {
            "gp5p95_rng": [(_NOW - 10, float(v), True) for v in [10, 30, 50, 70, 90, 200]],
        }
    )
    result = get_windowed_global_p5_p95_ratio(_WIN, store=store, now_ms=_NOW)
    assert 0.0 <= result <= 1.0 + 1e-9, f"ratio must be in [0,1]; got {result}"


def test_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_global_p5_p95_ratio(_WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "gp5p95_old": [(_NOW - _WIN - 100, 100.0, True)] * 5,
        }
    )
    assert get_windowed_global_p5_p95_ratio(_WIN, store=store, now_ms=_NOW) == 0.0


def test_single_call_ratio_is_one() -> None:
    """Single call -> p5 = p95 = that value -> ratio = 1.0."""
    _reset()
    store = _make_store(
        {
            "gp5p95_one": [(_NOW - 10, 50.0, True)],
        }
    )
    result = get_windowed_global_p5_p95_ratio(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"single call -> ratio=1.0; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"gp5p95_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 200]]})
    assert isinstance(get_windowed_global_p5_p95_ratio(_WIN, store=store, now_ms=_NOW), float)
