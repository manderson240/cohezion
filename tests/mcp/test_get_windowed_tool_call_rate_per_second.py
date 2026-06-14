"""Item 1091: get_windowed_tool_call_rate_per_second(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- call rate (calls/second) = (n-1) / span_seconds for n>=2 windowed calls.
0.0 for <2 calls or zero time span.

PRIMARY DISC.: 4 calls over 400ms span -> rate=(4-1)/0.4=7.5 calls/sec
  (PRIMARY DISC.: kills n/window_ms*1000: 4/400*1000=10 calls/sec -- divides by
   window size not actual span; kills n/span=(4/0.4)=10 -- includes one extra gap;
   correct rate=(n-1)/span_seconds=(3/0.4)=7.5).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_call_rate_per_second,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_call_rate_primary_discriminator() -> None:
    """PRIMARY DISC.: 4 calls over 400ms -> rate=7.5 calls/sec.

    Kills n/window=10 calls/sec (window size, not actual span).
    Kills n/span=10 (off-by-one: n-1 gaps, not n).
    Correct: (n-1)/span_s = 3/0.4 = 7.5.
    """
    _reset()
    store = _make_store(
        {
            "rate_disc": [
                (_NOW - 400, 10.0, True),
                (_NOW - 300, 20.0, True),
                (_NOW - 100, 30.0, True),
                (_NOW - 0, 40.0, True),
            ],
        }
    )
    result = get_windowed_tool_call_rate_per_second("rate_disc", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 7.5) < 1e-9, f"(n-1)/span=3/0.4=7.5; kills n/window=10; got {result}"


def test_call_rate_two_calls() -> None:
    """Two calls 200ms apart -> rate=1/0.2=5 calls/sec."""
    _reset()
    store = _make_store(
        {
            "rate_two": [
                (_NOW - 200, 10.0, True),
                (_NOW - 0, 20.0, True),
            ],
        }
    )
    result = get_windowed_tool_call_rate_per_second("rate_two", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 5.0) < 1e-9, f"1/0.2=5 calls/sec; got {result}"


def test_call_rate_single_call_returns_zero() -> None:
    """Single call -> <2 calls -> 0.0."""
    _reset()
    store = _make_store({"rate_single": [(_NOW - 100, 42.0, True)]})
    assert (
        get_windowed_tool_call_rate_per_second("rate_single", _WIN, store=store, now_ms=_NOW) == 0.0
    )


def test_call_rate_empty_window_returns_zero() -> None:
    """Empty window -> 0.0."""
    _reset()
    assert get_windowed_tool_call_rate_per_second("no_tool", _WIN, store={}, now_ms=_NOW) == 0.0


def test_call_rate_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "rate_old": [(_NOW - _WIN - 100, 10.0, True)] * 3,
        }
    )
    assert get_windowed_tool_call_rate_per_second("rate_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_call_rate_zero_span_returns_zero() -> None:
    """All calls at identical timestamps -> zero span -> 0.0."""
    _reset()
    store = _make_store(
        {
            "rate_same_ts": [(_NOW - 100, 10.0, True)] * 5,
        }
    )
    assert (
        get_windowed_tool_call_rate_per_second("rate_same_ts", _WIN, store=store, now_ms=_NOW)
        == 0.0
    )


def test_call_rate_unit() -> None:
    """Result units are calls/second (not calls/ms)."""
    _reset()
    # 3 calls over exactly 1 second (1000ms) span -> rate=2/1=2 calls/sec
    store = _make_store(
        {
            "rate_unit": [
                (_NOW - 1000, 10.0, True),
                (_NOW - 500, 20.0, True),
                (_NOW - 0, 30.0, True),
            ],
        }
    )
    result = get_windowed_tool_call_rate_per_second("rate_unit", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 2.0) < 1e-9, f"2 calls/sec; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "rate_rt": [(_NOW - float(d), 10.0, True) for d in [300, 200, 100, 0]],
        }
    )
    assert isinstance(
        get_windowed_tool_call_rate_per_second("rate_rt", _WIN, store=store, now_ms=_NOW), float
    )
