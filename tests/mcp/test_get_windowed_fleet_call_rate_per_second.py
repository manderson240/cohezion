"""Item 1092: get_windowed_fleet_call_rate_per_second(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide call rate (calls/s) = (n-1)/span_seconds where n=ALL pooled calls.
0.0 for <2 pooled calls or zero span. Fleet dual of item 1091.

PRIMARY DISC.: tool_a=[t-500,t-300], tool_b=[t-400,t-200,t-0]
  pooled sorted: [t-500,t-400,t-300,t-200,t-0]; n=5, span=500ms
  -> rate=(5-1)/0.5=8.0 calls/sec
  (PRIMARY DISC.: kills per-tool-avg: tool_a=5, tool_b=5, avg=5 calls/sec != 8;
   pooled uses all timestamps across tools; correct rate=8.0).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_call_rate_per_second,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_call_rate_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a 2 calls, tool_b 3 calls -> pooled 5 calls over 500ms = 8 calls/sec.

    Kills per-tool-avg = 5 calls/sec (each tool's rate=5, avg=5).
    Correct: pooled (n-1)/span_s = 4/0.5 = 8.0 calls/sec.
    """
    _reset()
    store = _make_store(
        {
            "fcrate_disc_a": [
                (_NOW - 500, 10.0, True),
                (_NOW - 300, 20.0, True),
            ],
            "fcrate_disc_b": [
                (_NOW - 400, 30.0, True),
                (_NOW - 200, 40.0, True),
                (_NOW - 0, 50.0, True),
            ],
        }
    )
    result = get_windowed_fleet_call_rate_per_second(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 8.0) < 1e-9, f"pooled rate=8.0; kills per-tool-avg=5.0; got {result}"


def test_fleet_call_rate_single_tool() -> None:
    """Single tool -> fleet rate equals that tool's rate."""
    _reset()
    store = _make_store(
        {
            "fcrate_single": [
                (_NOW - 500, 10.0, True),
                (_NOW - 0, 20.0, True),
            ],
        }
    )
    result = get_windowed_fleet_call_rate_per_second(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 2.0) < 1e-9, f"1/0.5s=2 calls/sec; got {result}"


def test_fleet_call_rate_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_fleet_call_rate_per_second(_WIN, store={}, now_ms=_NOW) == 0.0


def test_fleet_call_rate_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fcrate_old": [(_NOW - _WIN - 100, 10.0, True)] * 5,
        }
    )
    assert get_windowed_fleet_call_rate_per_second(_WIN, store=store, now_ms=_NOW) == 0.0


def test_fleet_call_rate_single_pooled_call_returns_zero() -> None:
    """Only one pooled call -> <2 -> 0.0."""
    _reset()
    store = _make_store({"fcrate_one": [(_NOW - 100, 10.0, True)]})
    assert get_windowed_fleet_call_rate_per_second(_WIN, store=store, now_ms=_NOW) == 0.0


def test_fleet_call_rate_zero_span_returns_zero() -> None:
    """All pooled calls at same timestamp -> zero span -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fcrate_same_a": [(_NOW - 100, 10.0, True)],
            "fcrate_same_b": [(_NOW - 100, 20.0, True)],
        }
    )
    assert get_windowed_fleet_call_rate_per_second(_WIN, store=store, now_ms=_NOW) == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fcrate_rt_a": [(_NOW - 500, 10.0, True)],
            "fcrate_rt_b": [(_NOW - 0, 20.0, True)],
        }
    )
    assert isinstance(
        get_windowed_fleet_call_rate_per_second(_WIN, store=store, now_ms=_NOW), float
    )
