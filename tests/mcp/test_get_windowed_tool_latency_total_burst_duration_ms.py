"""Item 1124: get_windowed_tool_latency_total_burst_duration_ms(tool_name, window_ms, burst_threshold_ms, *, store=None, now_ms=None) -> float
-- total time in bursts = sum of (last_ts - first_ts) for each burst run.
0.0 for empty window or zero bursts. Returns float.

PRIMARY DISC.: burst1 spans _NOW-800 to _NOW-600 = 200ms; burst2 single call = 0ms span
  -> total = 200ms
  (PRIMARY DISC.: kills burst_count=2 (count not time);
   kills mean_burst_length=1.5 (call count not ms);
   kills sum_of_lat_values=above-threshold-lat-sum (lat values, not timestamps);
   correct: for each burst run, span = last_ts - first_ts; sum spans; float=200ms).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_total_burst_duration_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0
_THR = 50.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_burst_duration_primary_discriminator() -> None:
    """PRIMARY DISC.: burst1=[_NOW-800,_NOW-700,_NOW-600]=200ms span; burst2=[_NOW-400]=0ms -> total=200ms."""
    _reset()
    store = _make_store(
        {
            "bd_disc": [
                (_NOW - 900, 10.0, True),  # low
                (_NOW - 800, 80.0, True),  # burst 1 start
                (_NOW - 700, 90.0, True),  # burst 1 middle
                (_NOW - 600, 85.0, True),  # burst 1 end (span = 800-600 = 200ms)
                (_NOW - 500, 10.0, True),  # exit
                (_NOW - 400, 70.0, True),  # burst 2 single call (span = 0ms)
                (_NOW - 300, 10.0, True),  # exit
            ],
        }
    )
    result = get_windowed_tool_latency_total_burst_duration_ms(
        "bd_disc", _WIN, _THR, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert abs(result - 200.0) < 1e-9, (
        f"burst1=200ms+burst2=0ms=200ms; kills count=2; kills mean_len=1.5; got {result}"
    )


def test_burst_duration_two_spans() -> None:
    """Two multi-call bursts: spans=[150,100] -> total=250ms."""
    _reset()
    store = _make_store(
        {
            "bd_two": [
                (_NOW - 800, 80.0, True),  # burst 1 start
                (
                    _NOW - 700,
                    80.0,
                    True,
                ),  # burst 1 end (150ms -> 800-700=100ms wait... 800-650=150)
                (_NOW - 650, 10.0, True),  # exit
                (_NOW - 500, 80.0, True),  # burst 2 start
                (_NOW - 400, 80.0, True),  # burst 2 end (800-650=150, 500-400=100)
                (_NOW - 300, 10.0, True),  # exit
            ],
        }
    )
    # burst1: _NOW-800 to _NOW-700 -> span=100ms
    # burst2: _NOW-500 to _NOW-400 -> span=100ms
    # total=200ms
    result = get_windowed_tool_latency_total_burst_duration_ms(
        "bd_two", _WIN, _THR, store=store, now_ms=_NOW
    )
    assert abs(result - 200.0) < 1e-9, f"burst1+burst2=100+100=200ms; got {result}"


def test_burst_duration_single_call_burst_is_zero() -> None:
    """A burst with just one call has span=0."""
    _reset()
    store = _make_store(
        {
            "bd_single": [
                (_NOW - 400, 80.0, True),  # single-call burst
                (_NOW - 300, 10.0, True),  # exit
            ],
        }
    )
    result = get_windowed_tool_latency_total_burst_duration_ms(
        "bd_single", _WIN, _THR, store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9, f"single-call burst -> span=0ms; got {result}"


def test_burst_duration_no_bursts_returns_zero() -> None:
    """No above-threshold calls -> 0.0."""
    _reset()
    store = _make_store(
        {
            "bd_none": [(_NOW - float(d), 30.0, True) for d in [300, 200, 100]],
        }
    )
    assert (
        get_windowed_tool_latency_total_burst_duration_ms(
            "bd_none", _WIN, _THR, store=store, now_ms=_NOW
        )
        == 0.0
    )


def test_burst_duration_empty_window_returns_zero() -> None:
    """Empty window -> 0.0."""
    _reset()
    assert (
        get_windowed_tool_latency_total_burst_duration_ms(
            "no_tool", _WIN, _THR, store={}, now_ms=_NOW
        )
        == 0.0
    )


def test_burst_duration_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "bd_old": [
                (_NOW - _WIN - 200, 80.0, True),  # outside
                (_NOW - _WIN - 100, 80.0, True),  # outside
            ],
        }
    )
    assert (
        get_windowed_tool_latency_total_burst_duration_ms(
            "bd_old", _WIN, _THR, store=store, now_ms=_NOW
        )
        == 0.0
    )


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "bd_rt": [
                (_NOW - 500, 80.0, True),  # burst start
                (_NOW - 300, 80.0, True),  # burst end (span=200ms)
                (_NOW - 200, 10.0, True),  # exit
            ],
        }
    )
    result = get_windowed_tool_latency_total_burst_duration_ms(
        "bd_rt", _WIN, _THR, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert abs(result - 200.0) < 1e-9
