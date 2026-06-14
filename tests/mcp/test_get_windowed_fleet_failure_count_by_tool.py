"""Item 1207: get_windowed_fleet_failure_count_by_tool(
              window_ms, tool_name, *, store=None, now_ms=None) -> int
-- per-tool count of FAILED calls (ok=False) within window.
Returns int. 0 for unknown/empty tool or no failed calls.
Formula: count(ok=False calls in window).
Composition: failure_count + success_count == total_call_count.

PRIMARY DISC.:
  tool_a: [(10ms,ok=T),(100ms,ok=F),(200ms,ok=F)] → failure_count=2
  tool_b: [(50ms,ok=T),(50ms,ok=T)] → failure_count=0
  failure_a=2 kills failure_b=0; kills always-0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_failure_count_by_tool,
    get_windowed_fleet_success_count_by_tool,
    get_windowed_fleet_total_call_count_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_failure_count_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: failure_a=2 kills failure_b=0; kills always-0."""
    _reset()
    store = _make_store(
        {
            "ffcbt_a": [
                (_NOW - 900, 10.0, True),  # success — excluded
                (_NOW - 600, 100.0, False),  # failure
                (_NOW - 300, 200.0, False),  # failure
            ],
            "ffcbt_b": [
                (_NOW - 700, 50.0, True),  # success — excluded
                (_NOW - 400, 50.0, True),  # success — excluded
            ],
        }
    )
    count_a = get_windowed_fleet_failure_count_by_tool(_WIN, "ffcbt_a", store=store, now_ms=_NOW)
    count_b = get_windowed_fleet_failure_count_by_tool(_WIN, "ffcbt_b", store=store, now_ms=_NOW)
    assert isinstance(count_a, int), f"expected int, got {type(count_a)}"
    assert count_a == 2, (
        f"failure_a=2 (two ok=False calls); kills failure_b=0/always-0; got {count_a}"
    )
    assert count_b == 0, f"failure_b=0 (no failures); got {count_b}"


def test_fleet_failure_count_excludes_successes() -> None:
    """Success calls do not count toward failure count."""
    _reset()
    store = _make_store(
        {
            "ffcbt_excl": [
                (_NOW - 900, 9999.0, True),  # success — should NOT count
                (_NOW - 600, 100.0, False),  # failure
                (_NOW - 300, 200.0, False),  # failure
            ],
        }
    )
    result = get_windowed_fleet_failure_count_by_tool(_WIN, "ffcbt_excl", store=store, now_ms=_NOW)
    assert result == 2, f"success excluded; count=(ok=F)=2; got {result}"


def test_fleet_failure_count_no_failures_returns_zero() -> None:
    """All calls succeeded → no failures → 0."""
    _reset()
    store = _make_store(
        {
            "ffcbt_ok": [
                (_NOW - 900, 10.0, True),
                (_NOW - 600, 20.0, True),
            ],
        }
    )
    result = get_windowed_fleet_failure_count_by_tool(_WIN, "ffcbt_ok", store=store, now_ms=_NOW)
    assert result == 0
    assert isinstance(result, int)


def test_fleet_failure_count_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0."""
    _reset()
    store = _make_store(
        {
            "ffcbt_other": [(_NOW - 500, 100.0, False)],
        }
    )
    result = get_windowed_fleet_failure_count_by_tool(_WIN, "nonexistent", store=store, now_ms=_NOW)
    assert result == 0
    assert isinstance(result, int)


def test_fleet_failure_count_empty_store_returns_zero() -> None:
    """Empty store → 0."""
    _reset()
    result = get_windowed_fleet_failure_count_by_tool(_WIN, "any_tool", store={}, now_ms=_NOW)
    assert result == 0


def test_fleet_failure_count_outside_window_returns_zero() -> None:
    """All calls outside window → 0."""
    _reset()
    store = _make_store(
        {
            "ffcbt_old": [
                (_NOW - _WIN - 200, 100.0, False),
                (_NOW - _WIN - 100, 200.0, False),
            ],
        }
    )
    result = get_windowed_fleet_failure_count_by_tool(_WIN, "ffcbt_old", store=store, now_ms=_NOW)
    assert result == 0


def test_fleet_failure_count_composition_identity() -> None:
    """failure_count + success_count == total_call_count."""
    _reset()
    store = _make_store(
        {
            "ffcbt_comp": [
                (_NOW - 900, 10.0, True),  # success
                (_NOW - 700, 100.0, False),  # failure
                (_NOW - 500, 20.0, True),  # success
                (_NOW - 300, 200.0, False),  # failure
                (_NOW - 100, 30.0, True),  # success
            ],
        }
    )
    fail_cnt = get_windowed_fleet_failure_count_by_tool(
        _WIN, "ffcbt_comp", store=store, now_ms=_NOW
    )
    succ_cnt = get_windowed_fleet_success_count_by_tool(
        _WIN, "ffcbt_comp", store=store, now_ms=_NOW
    )
    total = get_windowed_fleet_total_call_count_by_tool(
        _WIN, "ffcbt_comp", store=store, now_ms=_NOW
    )
    assert fail_cnt == 2, f"2 failures; got {fail_cnt}"
    assert succ_cnt == 3, f"3 successes; got {succ_cnt}"
    assert fail_cnt + succ_cnt == total, f"composition: {fail_cnt}+{succ_cnt} != {total}"


def test_returns_int_type() -> None:
    """Return type is int."""
    _reset()
    store = _make_store(
        {
            "ffcbt_rt": [
                (_NOW - 400, 80.0, False),  # failure
                (_NOW - 200, 50.0, True),  # success
            ],
        }
    )
    result = get_windowed_fleet_failure_count_by_tool(_WIN, "ffcbt_rt", store=store, now_ms=_NOW)
    assert isinstance(result, int)
    assert result == 1
