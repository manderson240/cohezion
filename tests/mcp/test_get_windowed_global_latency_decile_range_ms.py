"""Item 1056: get_windowed_global_latency_decile_range_ms(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide D9-D1 (global_p90 - global_p10) inter-decile range (pooled).

Thin composition: global_p90 - global_p10. 0.0 for empty pool.
Fleet dual of per-tool item 1055. Injectable store. Pure function.

PRIMARY DISC.: tool_a=[10,20,30]+tool_b=[70,80,90,100]
  pooled=[10,20,30,70,80,90,100] n=7
  p10: idx=0.1*6=0.6 -> 10+0.6*(20-10)=16.0
  p90: idx=0.9*6=5.4 -> 90+0.4*(100-90)=94.0
  decile_range=94.0-16.0=78.0
  (PRIMARY DISC.: kills per-tool D9-D1 then avg: tool_a n=3 p10≈10.4 p90≈29.6 range≈19.2,
     tool_b n=4 p10=72.5 p90=97.5 range=25.0, avg≈22.1 ≠ 78.0;
   kills range=max-min=90 (too wide);
   correct pooled D9-D1=94.0-16.0=78.0).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_decile_range_ms,
    get_windowed_global_latency_percentile,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_decile_range_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a=[10,20,30]+tool_b=[70,80,90,100] -> pooled D9-D1=78.0.

    Kills per-tool D9-D1 avg≈22.1 (NOT pooled).
    Kills range=max-min=90.
    Correct: pooled p10=16.0, p90=94.0, D9-D1=78.0.
    """
    _reset()
    store = _make_store(
        {
            "gdr_a": [(_NOW - 10, float(v), True) for v in [10, 20, 30]],
            "gdr_b": [(_NOW - 10, float(v), True) for v in [70, 80, 90, 100]],
        }
    )
    result = get_windowed_global_latency_decile_range_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 78.0) < 1e-9, (
        f"pooled D9-D1=78.0; kills per-tool-avg≈22.1 and range=90; got {result}"
    )


def test_decile_range_equals_p90_minus_p10() -> None:
    """decile_range == global_p90 - global_p10 (arithmetic identity)."""
    _reset()
    store = _make_store(
        {
            "gdr_id": [(_NOW - 10, float(v), True) for v in [10, 20, 50, 100, 200]],
        }
    )
    result = get_windowed_global_latency_decile_range_ms(_WIN, store=store, now_ms=_NOW)
    p10 = get_windowed_global_latency_percentile(10.0, _WIN, store=store, now_ms=_NOW)
    p90 = get_windowed_global_latency_percentile(90.0, _WIN, store=store, now_ms=_NOW)
    assert abs(result - (p90 - p10)) < 1e-9, f"decile_range={result} != p90-p10={p90 - p10}"


def test_all_equal_pooled_decile_range_zero() -> None:
    """All equal pooled -> p10=p90 -> decile_range=0.0."""
    _reset()
    store = _make_store(
        {
            "gdr_eq": [(_NOW - 10, 50.0, True)] * 8,
        }
    )
    result = get_windowed_global_latency_decile_range_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 0.0) < 1e-9, f"all-equal -> decile_range=0.0; got {result}"


def test_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_global_latency_decile_range_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "gdr_old": [(_NOW - _WIN - 100, 50.0, True)] * 5,
        }
    )
    assert get_windowed_global_latency_decile_range_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_decile_range_non_negative() -> None:
    """Decile range >= 0 (p90 >= p10 always)."""
    _reset()
    store = _make_store(
        {
            "gdr_pos": [(_NOW - 10, float(v), True) for v in [10, 50, 200, 50, 10]],
        }
    )
    result = get_windowed_global_latency_decile_range_ms(_WIN, store=store, now_ms=_NOW)
    assert result >= 0.0, f"decile range must be non-negative; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"gdr_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 200]]})
    assert isinstance(
        get_windowed_global_latency_decile_range_ms(_WIN, store=store, now_ms=_NOW), float
    )
