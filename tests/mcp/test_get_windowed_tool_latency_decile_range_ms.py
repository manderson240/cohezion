"""Item 1055: get_windowed_tool_latency_decile_range_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- per-tool D9-D1 (p90-p10) inter-decile range.

Thin composition: p90 - p10. Wider than IQR (p75-p25) but tighter than full range.
0.0 for unknown/empty tool. Injectable store. Pure function.

PRIMARY DISC.: lats [10,20,...,100] n=10
  p10: idx=0.1*9=0.9 -> 10+0.9*(20-10)=19.0
  p90: idx=0.9*9=8.1 -> 90+0.1*(100-90)=91.0
  decile_range = 91.0 - 19.0 = 72.0
  (PRIMARY DISC.: kills IQR=p75-p25=45.0 (narrower interval);
   kills range=max-min=90 (too wide);
   correct D9-D1=91.0-19.0=72.0).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_decile_range_ms,
    get_windowed_tool_p10_ms,
    get_windowed_tool_p90_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_decile_range_primary_discriminator() -> None:
    """PRIMARY DISC.: [10..100] n=10 -> decile_range=91.0-19.0=72.0.

    Kills IQR=45.0 (narrower p75-p25).
    Kills range=90 (max-min too wide).
    Correct: D9-D1=p90-p10=91.0-19.0=72.0.
    """
    _reset()
    store = _make_store(
        {
            "dr_disc": [(_NOW - 10, float(v), True) for v in range(10, 101, 10)],
        }
    )
    result = get_windowed_tool_latency_decile_range_ms("dr_disc", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 72.0) < 1e-9, (
        f"decile_range=72.0; kills IQR=45.0 and range=90; got {result}"
    )


def test_decile_range_equals_p90_minus_p10() -> None:
    """decile_range == p90 - p10 (arithmetic identity)."""
    _reset()
    lats = [10.0, 20.0, 50.0, 100.0, 200.0, 500.0]
    store = _make_store(
        {
            "dr_id": [(_NOW - 10, v, True) for v in lats],
        }
    )
    result = get_windowed_tool_latency_decile_range_ms("dr_id", _WIN, store=store, now_ms=_NOW)
    p10 = get_windowed_tool_p10_ms("dr_id", _WIN, store=store, now_ms=_NOW)
    p90 = get_windowed_tool_p90_ms("dr_id", _WIN, store=store, now_ms=_NOW)
    assert abs(result - (p90 - p10)) < 1e-9, f"decile_range={result} != p90-p10={p90 - p10}"


def test_all_equal_decile_range_zero() -> None:
    """All equal -> p10=p90 -> decile_range=0.0."""
    _reset()
    store = _make_store(
        {
            "dr_eq": [(_NOW - 10, 50.0, True)] * 6,
        }
    )
    result = get_windowed_tool_latency_decile_range_ms("dr_eq", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 0.0) < 1e-9, f"all-equal -> decile_range=0.0; got {result}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert (
        get_windowed_tool_latency_decile_range_ms("no_such_dr", _WIN, store={}, now_ms=_NOW) == 0.0
    )


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "dr_old": [(_NOW - _WIN - 100, 50.0, True)] * 5,
        }
    )
    assert (
        get_windowed_tool_latency_decile_range_ms("dr_old", _WIN, store=store, now_ms=_NOW) == 0.0
    )


def test_decile_range_non_negative() -> None:
    """Decile range >= 0 (p90 >= p10 always)."""
    _reset()
    store = _make_store(
        {
            "dr_pos": [(_NOW - 10, float(v), True) for v in [10, 50, 200]],
        }
    )
    result = get_windowed_tool_latency_decile_range_ms("dr_pos", _WIN, store=store, now_ms=_NOW)
    assert result >= 0.0, f"decile range must be non-negative; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"dr_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 200]]})
    assert isinstance(
        get_windowed_tool_latency_decile_range_ms("dr_rt", _WIN, store=store, now_ms=_NOW), float
    )
