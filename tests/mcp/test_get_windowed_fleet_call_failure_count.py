"""Item 1108: get_windowed_fleet_call_failure_count(window_ms, *, store=None, now_ms=None) -> int
-- fleet-wide count of windowed calls with success=False across ALL tools.
Returns int. 0 for empty window.

PRIMARY DISC.: tool_a has 1 failure, tool_b has 2 failures -> fleet_count=3
  (PRIMARY DISC.: kills per-tool-max=2 (max not sum);
   kills per-tool-first=1 (only first tool counted);
   kills 0 (inverted logic, counts successes);
   correct: pool ALL records across all tools, count ok==False, return int=3).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_call_failure_count,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_failure_count_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a 1 failure + tool_b 2 failures -> fleet_count=3.

    Kills per-tool-max=2; kills per-tool-first=1; kills inverted=5 (successes).
    """
    _reset()
    store = _make_store(
        {
            "fa_a": [
                (_NOW - 500, 10.0, False),  # FAILURE
                (_NOW - 400, 10.0, True),  # success
                (_NOW - 300, 10.0, True),  # success
            ],
            "fa_b": [
                (_NOW - 250, 10.0, True),  # success
                (_NOW - 150, 10.0, False),  # FAILURE
                (_NOW - 100, 10.0, False),  # FAILURE
            ],
        }
    )
    result = get_windowed_fleet_call_failure_count(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, int)
    assert result == 3, f"1+2=3 fleet failures; kills max=2; kills first-only=1; got {result}"


def test_fleet_failure_count_all_failures() -> None:
    """Every call in the fleet is a failure -> count = total calls."""
    _reset()
    store = _make_store(
        {
            "fa_all_a": [(_NOW - float(d), 10.0, False) for d in [300, 200]],
            "fa_all_b": [(_NOW - float(d), 10.0, False) for d in [150, 100, 50]],
        }
    )
    assert get_windowed_fleet_call_failure_count(_WIN, store=store, now_ms=_NOW) == 5


def test_fleet_failure_count_no_failures() -> None:
    """All calls succeed -> 0."""
    _reset()
    store = _make_store(
        {
            "fa_none_a": [(_NOW - float(d), 10.0, True) for d in [300, 200]],
            "fa_none_b": [(_NOW - float(d), 10.0, True) for d in [150, 100]],
        }
    )
    assert get_windowed_fleet_call_failure_count(_WIN, store=store, now_ms=_NOW) == 0


def test_fleet_failure_count_empty_store_returns_zero() -> None:
    """Empty store -> 0."""
    _reset()
    assert get_windowed_fleet_call_failure_count(_WIN, store={}, now_ms=_NOW) == 0


def test_fleet_failure_count_outside_window_returns_zero() -> None:
    """All calls outside window -> 0."""
    _reset()
    store = _make_store(
        {
            "fa_old_a": [(_NOW - _WIN - 100, 10.0, False)] * 3,
            "fa_old_b": [(_NOW - _WIN - 200, 10.0, False)] * 2,
        }
    )
    assert get_windowed_fleet_call_failure_count(_WIN, store=store, now_ms=_NOW) == 0


def test_fleet_failure_count_respects_window_boundary() -> None:
    """Only calls with ts >= cutoff are counted."""
    _reset()
    store = _make_store(
        {
            "fa_bnd": [
                (_NOW - _WIN - 1, 10.0, False),  # outside: NOT counted
                (_NOW - _WIN, 10.0, False),  # exactly at cutoff: counted
                (_NOW - 500, 10.0, False),  # inside: counted
                (_NOW - 100, 10.0, True),  # inside but success: NOT counted
            ],
        }
    )
    result = get_windowed_fleet_call_failure_count(_WIN, store=store, now_ms=_NOW)
    assert result == 2, f"2 failures in window; got {result}"


def test_returns_int_type() -> None:
    """Return type is int."""
    _reset()
    store = _make_store(
        {
            "fa_rt": [(_NOW - 100, 10.0, False), (_NOW - 50, 10.0, True)],
        }
    )
    result = get_windowed_fleet_call_failure_count(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, int)
    assert result == 1
