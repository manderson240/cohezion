"""Item 1089: get_windowed_tool_call_gap_max_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- maximum gap (ms) between consecutive calls in the window.
0.0 for <2 calls. Useful for detecting stalls/timeouts.

PRIMARY DISC.: calls at ts=[t-400, t-300, t-100, t-0] -> gaps=[100, 200, 100]
  -> max_gap=200.0 ms
  (PRIMARY DISC.: kills mean_gap=400/3≈133.3ms (not max);
   kills last_gap=100ms (most recent gap, not max);
   correct max_gap=200.0ms between t-300 and t-100).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_call_gap_max_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_call_gap_max_primary_discriminator() -> None:
    """PRIMARY DISC.: ts=[t-400,t-300,t-100,t-0] -> max_gap=200.0 ms.

    Kills mean_gap=400/3≈133.3ms (not max).
    Kills last_gap=100ms (most recent, not max).
    Correct: max_gap=200.0ms (between t-300 and t-100).
    """
    _reset()
    store = _make_store(
        {
            "gap_disc": [
                (_NOW - 400, 10.0, True),
                (_NOW - 300, 20.0, True),
                (_NOW - 100, 30.0, True),
                (_NOW - 0, 40.0, True),
            ],
        }
    )
    result = get_windowed_tool_call_gap_max_ms("gap_disc", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 200.0) < 1e-9, (
        f"max_gap=200ms; kills mean=133.3ms; kills last=100ms; got {result}"
    )


def test_call_gap_max_equally_spaced_calls() -> None:
    """Equally spaced calls -> all gaps equal -> max = that gap."""
    _reset()
    store = _make_store(
        {
            "gap_equal": [(_NOW - float(d), 10.0, True) for d in [300, 200, 100, 0]],
        }
    )
    result = get_windowed_tool_call_gap_max_ms("gap_equal", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 100.0) < 1e-9, f"equal gaps=100ms; got {result}"


def test_call_gap_max_single_call_returns_zero() -> None:
    """Single call -> no gaps -> 0.0."""
    _reset()
    store = _make_store({"gap_single": [(_NOW - 100, 42.0, True)]})
    assert get_windowed_tool_call_gap_max_ms("gap_single", _WIN, store=store, now_ms=_NOW) == 0.0


def test_call_gap_max_empty_window_returns_zero() -> None:
    """Empty window -> 0.0."""
    _reset()
    assert get_windowed_tool_call_gap_max_ms("no_tool", _WIN, store={}, now_ms=_NOW) == 0.0


def test_call_gap_max_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "gap_old": [(_NOW - _WIN - 100, 10.0, True)] * 3,
        }
    )
    assert get_windowed_tool_call_gap_max_ms("gap_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_call_gap_max_two_calls() -> None:
    """Two calls -> one gap -> max = that gap."""
    _reset()
    store = _make_store(
        {
            "gap_two": [
                (_NOW - 250, 10.0, True),
                (_NOW - 50, 20.0, True),
            ],
        }
    )
    result = get_windowed_tool_call_gap_max_ms("gap_two", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 200.0) < 1e-9, f"single gap=200ms; got {result}"


def test_call_gap_max_uses_timestamp_not_latency() -> None:
    """Max gap is determined by TIMESTAMPS of calls, not by latency values."""
    _reset()
    # Large latency, small time gap vs small latency, large time gap
    store = _make_store(
        {
            "gap_ts": [
                (_NOW - 500, 500.0, True),  # ts diff to next: 400ms (large gap)
                (_NOW - 100, 1.0, True),  # ts diff to next: 100ms (small gap)
                (_NOW - 0, 1.0, True),
            ],
        }
    )
    result = get_windowed_tool_call_gap_max_ms("gap_ts", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 400.0) < 1e-9, f"max time gap=400ms; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "gap_rt": [(_NOW - float(d), 10.0, True) for d in [200, 100, 0]],
        }
    )
    assert isinstance(
        get_windowed_tool_call_gap_max_ms("gap_rt", _WIN, store=store, now_ms=_NOW), float
    )
