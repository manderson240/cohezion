"""Item 1107: get_windowed_tool_call_failure_count(tool_name, window_ms, *, store=None, now_ms=None) -> int
-- count of windowed calls with success=False.
Returns int. 0 for empty window.

PRIMARY DISC.: 5 calls, 2 with ok=False -> count=2
  (PRIMARY DISC.: kills success_count=3 (counts True not False);
   kills total_count=5 (counts all calls regardless of ok);
   kills failure_rate=0.4 (fraction not count);
   correct: count ok==False in window, return int=2).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_call_failure_count,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_failure_count_primary_discriminator() -> None:
    """PRIMARY DISC.: 2 failures out of 5 calls -> count=2.

    Kills success_count=3, total_count=5, failure_rate=0.4.
    """
    _reset()
    store = _make_store(
        {
            "fc_disc": [
                (_NOW - 500, 10.0, True),  # success
                (_NOW - 400, 20.0, False),  # FAILURE
                (_NOW - 300, 30.0, True),  # success
                (_NOW - 200, 40.0, False),  # FAILURE
                (_NOW - 100, 50.0, True),  # success
            ],
        }
    )
    result = get_windowed_tool_call_failure_count("fc_disc", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, int)
    assert result == 2, f"2 failures; kills success=3; kills total=5; kills rate=0.4; got {result}"


def test_failure_count_all_failures() -> None:
    """All calls fail -> count = n."""
    _reset()
    store = _make_store(
        {
            "fc_all": [(_NOW - float(d), 10.0, False) for d in [300, 200, 100]],
        }
    )
    assert get_windowed_tool_call_failure_count("fc_all", _WIN, store=store, now_ms=_NOW) == 3


def test_failure_count_no_failures() -> None:
    """All calls succeed -> 0."""
    _reset()
    store = _make_store(
        {
            "fc_none": [(_NOW - float(d), 10.0, True) for d in [300, 200, 100]],
        }
    )
    assert get_windowed_tool_call_failure_count("fc_none", _WIN, store=store, now_ms=_NOW) == 0


def test_failure_count_empty_window_returns_zero() -> None:
    """Empty window -> 0."""
    _reset()
    assert get_windowed_tool_call_failure_count("no_tool", _WIN, store={}, now_ms=_NOW) == 0


def test_failure_count_outside_window_returns_zero() -> None:
    """All calls outside window -> 0."""
    _reset()
    store = _make_store(
        {
            "fc_old": [(_NOW - _WIN - 100, 10.0, False)] * 5,
        }
    )
    assert get_windowed_tool_call_failure_count("fc_old", _WIN, store=store, now_ms=_NOW) == 0


def test_failure_count_respects_window_boundary() -> None:
    """Only calls within window are counted."""
    _reset()
    store = _make_store(
        {
            "fc_boundary": [
                (_NOW - _WIN - 1, 10.0, False),  # outside: NOT counted
                (_NOW - _WIN, 10.0, False),  # exactly at cutoff: counted (ts >= cutoff)
                (_NOW - 500, 10.0, False),  # inside: counted
                (_NOW - 100, 10.0, True),  # inside but success: NOT counted
            ],
        }
    )
    result = get_windowed_tool_call_failure_count("fc_boundary", _WIN, store=store, now_ms=_NOW)
    assert result == 2, f"2 failures in window; got {result}"


def test_returns_int_type() -> None:
    """Return type is int."""
    _reset()
    store = _make_store(
        {
            "fc_rt": [(_NOW - 100, 10.0, False)],
        }
    )
    result = get_windowed_tool_call_failure_count("fc_rt", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, int)
    assert result == 1
