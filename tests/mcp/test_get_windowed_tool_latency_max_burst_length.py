"""Item 1084: get_windowed_tool_latency_max_burst_length(tool_name, window_ms, burst_threshold_ms, *, store=None, now_ms=None) -> int
-- length (in calls) of the longest consecutive run of above-threshold latency calls.
0 if no above-threshold calls.

PRIMARY DISC.: lats=[10,80,90,20,70,85,95,100,15] threshold=50
  -> runs=[80,90]=len2, [70,85,95,100]=len4 -> max_burst_length=4
  (PRIMARY DISC.: kills burst_count=2 -- number of runs, not max length;
   kills total-above=6 -- individual call count;
   correct max_burst_length=4).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_max_burst_length,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_max_burst_primary_discriminator() -> None:
    """PRIMARY DISC.: [10,80,90,20,70,85,95,100,15] threshold=50 -> max_burst=4.

    Kills burst_count=2 (number of runs, not max length).
    Kills total-above=6 (individual calls, not max run).
    Correct: max_burst_length=4.
    """
    _reset()
    lats = [10.0, 80.0, 90.0, 20.0, 70.0, 85.0, 95.0, 100.0, 15.0]
    store = _make_store({
        "mbl_disc": [
            (_NOW - (len(lats) - 1 - i) * 50.0, lat, True)
            for i, lat in enumerate(lats)
        ],
    })
    result = get_windowed_tool_latency_max_burst_length("mbl_disc", _WIN, 50.0, store=store, now_ms=_NOW)
    assert isinstance(result, int)
    assert result == 4, (
        f"max_burst=4 (run of [70,85,95,100]); kills count=2; kills total=6; got {result}"
    )


def test_max_burst_single_isolated_calls() -> None:
    """All bursts are single calls -> max_burst_length=1."""
    _reset()
    lats = [10.0, 80.0, 5.0, 70.0, 15.0, 60.0]
    store = _make_store({
        "mbl_single": [
            (_NOW - (len(lats) - 1 - i) * 50.0, lat, True)
            for i, lat in enumerate(lats)
        ],
    })
    result = get_windowed_tool_latency_max_burst_length("mbl_single", _WIN, 50.0, store=store, now_ms=_NOW)
    assert result == 1, f"only isolated above-threshold -> max=1; got {result}"


def test_max_burst_all_above_threshold() -> None:
    """All calls above threshold -> max_burst = total number of calls."""
    _reset()
    store = _make_store({
        "mbl_all": [(_NOW - float(d), 100.0, True) for d in [400, 300, 200, 100, 0]],
    })
    result = get_windowed_tool_latency_max_burst_length("mbl_all", _WIN, 50.0, store=store, now_ms=_NOW)
    assert result == 5, f"all above threshold -> max_burst=5; got {result}"


def test_max_burst_no_above_threshold_returns_zero() -> None:
    """No calls above threshold -> 0."""
    _reset()
    store = _make_store({
        "mbl_none": [(_NOW - float(d), 10.0, True) for d in [300, 200, 100, 0]],
    })
    assert get_windowed_tool_latency_max_burst_length("mbl_none", _WIN, 50.0, store=store, now_ms=_NOW) == 0


def test_max_burst_empty_window_returns_zero() -> None:
    """Empty window -> 0."""
    _reset()
    assert get_windowed_tool_latency_max_burst_length("no_tool", _WIN, 50.0, store={}, now_ms=_NOW) == 0


def test_max_burst_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0."""
    _reset()
    store = _make_store({
        "mbl_old": [(_NOW - _WIN - 100, 200.0, True)] * 5,
    })
    assert get_windowed_tool_latency_max_burst_length("mbl_old", _WIN, 50.0, store=store, now_ms=_NOW) == 0


def test_max_burst_threshold_boundary_exclusive() -> None:
    """Calls at exactly threshold do NOT count (strictly > required)."""
    _reset()
    store = _make_store({
        "mbl_bound": [
            (_NOW - 200, 50.0, True),   # at threshold -- not above
            (_NOW - 100, 51.0, True),   # above -- burst of 1
            (_NOW - 0, 50.0, True),     # at threshold -- not above
        ],
    })
    result = get_windowed_tool_latency_max_burst_length("mbl_bound", _WIN, 50.0, store=store, now_ms=_NOW)
    assert result == 1, f"only 51.0 above 50 -> max=1; got {result}"


def test_returns_int_type() -> None:
    """Return type is int."""
    _reset()
    lats = [10.0, 80.0, 90.0, 20.0, 70.0]
    store = _make_store({
        "mbl_rt": [
            (_NOW - (len(lats) - 1 - i) * 50.0, lat, True)
            for i, lat in enumerate(lats)
        ],
    })
    result = get_windowed_tool_latency_max_burst_length("mbl_rt", _WIN, 50.0, store=store, now_ms=_NOW)
    assert isinstance(result, int)
