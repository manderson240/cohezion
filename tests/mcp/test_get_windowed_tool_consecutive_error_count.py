"""Item 1014: get_windowed_tool_consecutive_error_count(tool_name, window_ms, *, store=None, now_ms=None) -> int
-- number of consecutive errors at the END of the window (most-recent calls).

Detects active error storms. 0 when last call succeeded or no recent calls.
Counts from most-recent call backwards until a success is found.
Injectable store. Pure function.

PRIMARY DISC.: records (ts ascending = older to newer in window)
  [True, False, True, False, False] -> consecutive errors at END = 2 (not total=3).
  Kills total_error_count=3 (total errors != consecutive at end).
  Kills any impl that counts ALL errors without checking continuity from end.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_consecutive_error_count,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_consecutive_error_primary_discriminator() -> None:
    """PRIMARY DISC.: [True, False, True, False, False] (oldest->newest) -> 2.

    total_errors=3 but consecutive_at_end=2 (stopped at the True in middle).
    Kills impl returning total_error_count=3.
    Kills impl returning total_consecutive_from_start.
    """
    _reset()
    # timestamps must be ordered: older ts -> earlier call, newer ts -> later call
    store = _make_store(
        {
            "cec_a": [
                (_NOW - 50, 10.0, True),  # oldest: success — stops the streak
                (_NOW - 40, 20.0, False),  # error
                (_NOW - 30, 30.0, True),  # success — resets streak
                (_NOW - 20, 40.0, False),  # error
                (_NOW - 10, 50.0, False),  # most recent: error (streak=2)
            ],
        }
    )
    result = get_windowed_tool_consecutive_error_count("cec_a", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, int)
    assert result == 2, f"consecutive_at_end=2 (not total=3); kills total_count=3; got {result}"


def test_all_errors_returns_full_count() -> None:
    """All calls errored -> consecutive == total call count."""
    _reset()
    store = _make_store(
        {
            "cec_all": [
                (_NOW - 30, 10.0, False),
                (_NOW - 20, 20.0, False),
                (_NOW - 10, 30.0, False),
            ],
        }
    )
    result = get_windowed_tool_consecutive_error_count("cec_all", _WIN, store=store, now_ms=_NOW)
    assert result == 3, f"all errors -> streak=3; got {result}"


def test_last_call_success_returns_zero() -> None:
    """Last call succeeded -> consecutive error streak = 0."""
    _reset()
    store = _make_store(
        {
            "cec_end_ok": [
                (_NOW - 30, 10.0, False),
                (_NOW - 20, 20.0, False),
                (_NOW - 10, 30.0, True),  # most recent: success
            ],
        }
    )
    result = get_windowed_tool_consecutive_error_count("cec_end_ok", _WIN, store=store, now_ms=_NOW)
    assert result == 0, f"last call succeeded -> streak=0; got {result}"


def test_single_error_returns_one() -> None:
    """One error, nothing else in window -> streak=1."""
    _reset()
    store = _make_store(
        {
            "cec_one": [(_NOW - 10, 10.0, False)],
        }
    )
    result = get_windowed_tool_consecutive_error_count("cec_one", _WIN, store=store, now_ms=_NOW)
    assert result == 1, f"single error -> streak=1; got {result}"


def test_single_success_returns_zero() -> None:
    """One success -> streak=0."""
    _reset()
    store = _make_store(
        {
            "cec_ok": [(_NOW - 10, 10.0, True)],
        }
    )
    result = get_windowed_tool_consecutive_error_count("cec_ok", _WIN, store=store, now_ms=_NOW)
    assert result == 0, f"single success -> streak=0; got {result}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0."""
    _reset()
    assert (
        get_windowed_tool_consecutive_error_count("no_such_cec", _WIN, store={}, now_ms=_NOW) == 0
    )


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0."""
    _reset()
    store = _make_store(
        {
            "cec_old": [(_NOW - _WIN - 100, 10.0, False)] * 5,
        }
    )
    assert get_windowed_tool_consecutive_error_count("cec_old", _WIN, store=store, now_ms=_NOW) == 0


def test_streak_breaks_at_success_not_at_window_boundary() -> None:
    """Streak counts from end; stops at any success before window start.

    [True, False, False] (all in window) -> streak=2 (stops at the True).
    Tests that windowing doesn't artificially extend the streak.
    """
    _reset()
    store = _make_store(
        {
            "cec_break": [
                (_NOW - 30, 10.0, True),
                (_NOW - 20, 20.0, False),
                (_NOW - 10, 30.0, False),
            ],
        }
    )
    result = get_windowed_tool_consecutive_error_count("cec_break", _WIN, store=store, now_ms=_NOW)
    assert result == 2, f"streak stops at True -> 2; got {result}"


def test_returns_int_type() -> None:
    """Return type is int."""
    _reset()
    store = _make_store({"cec_rt": [(_NOW - 10, 10.0, False)] * 3})
    assert isinstance(
        get_windowed_tool_consecutive_error_count("cec_rt", _WIN, store=store, now_ms=_NOW), int
    )
