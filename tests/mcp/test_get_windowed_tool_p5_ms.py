"""Item 1043: get_windowed_tool_p5_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- 5th-percentile latency for a single tool in the window.

Thin delegate: get_windowed_latency_percentile(tool_name, 5.0, window_ms, ...).
0.0 for unknown/empty tool. Injectable store. Pure function.

PRIMARY DISC.: lats [10,20,30,40,50,60,70,80,90,100] n=10
  p5 = idx = 0.05*(10-1) = 0.45 -> 10 + 0.45*(20-10) = 14.5
  (PRIMARY DISC.: kills p10=19.0 (wrong percentile);
   kills p5=10.0 (nearest-rank no-interpolation);
   correct p5=14.5 via linear interpolation).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_p5_ms,
    get_windowed_tool_p10_ms,
    get_windowed_latency_percentile,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_p5_primary_discriminator() -> None:
    """PRIMARY DISC.: [10..100] step=10 -> p5=14.5.

    Kills p10=19.0 (wrong, one decile higher).
    Kills p5=10.0 (nearest-rank, no interpolation).
    Correct: linear interp idx=0.45 -> 10+0.45*10=14.5.
    """
    _reset()
    store = _make_store({
        "p5_a": [(_NOW - 10, float(v), True) for v in range(10, 101, 10)],
    })
    result = get_windowed_tool_p5_ms("p5_a", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 14.5) < 1e-9, (
        f"p5=14.5; kills p10=19.0 and nearest-rank=10.0; got {result}"
    )


def test_p5_less_than_p10() -> None:
    """p5 <= p10 always (ordering invariant)."""
    _reset()
    store = _make_store({
        "p5_ord": [(_NOW - 10, float(v), True) for v in range(10, 101, 10)],
    })
    p5 = get_windowed_tool_p5_ms("p5_ord", _WIN, store=store, now_ms=_NOW)
    p10 = get_windowed_tool_p10_ms("p5_ord", _WIN, store=store, now_ms=_NOW)
    assert p5 <= p10, f"p5={p5} must be <= p10={p10}"


def test_p5_matches_percentile_delegate() -> None:
    """p5 == get_windowed_latency_percentile(tool, 5.0, ...) exactly."""
    _reset()
    lats = [10.0, 20.0, 50.0, 100.0, 200.0, 500.0]
    store = _make_store({
        "p5_del": [(_NOW - 10, v, True) for v in lats],
    })
    p5 = get_windowed_tool_p5_ms("p5_del", _WIN, store=store, now_ms=_NOW)
    direct = get_windowed_latency_percentile("p5_del", 5.0, _WIN, store=store, now_ms=_NOW)
    assert abs(p5 - direct) < 1e-9, f"p5={p5} != direct percentile={direct}"


def test_single_call_p5_equals_value() -> None:
    """Single call -> p5 = that value (only one sample)."""
    _reset()
    store = _make_store({
        "p5_one": [(_NOW - 10, 75.0, True)],
    })
    result = get_windowed_tool_p5_ms("p5_one", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 75.0) < 1e-9, f"single call -> p5=75.0; got {result}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_p5_ms("no_such_p5", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "p5_old": [(_NOW - _WIN - 100, 100.0, True)] * 5,
    })
    assert get_windowed_tool_p5_ms("p5_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_all_equal_p5_equals_value() -> None:
    """All equal latencies -> p5 = that value."""
    _reset()
    store = _make_store({
        "p5_eq": [(_NOW - 10, 50.0, True)] * 6,
    })
    result = get_windowed_tool_p5_ms("p5_eq", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 50.0) < 1e-9, f"all-equal -> p5=50.0; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"p5_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 200]]})
    assert isinstance(get_windowed_tool_p5_ms("p5_rt", _WIN, store=store, now_ms=_NOW), float)
