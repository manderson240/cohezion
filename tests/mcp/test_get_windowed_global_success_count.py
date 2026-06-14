"""Item 971: get_windowed_global_success_count(window_ms, *, store=None, now_ms=None) -> int
-- total successful calls fleet-wide in window.

PRIMARY DISC.: tool_a 3 successes + tool_b 2 successes -> 5 (not total calls, not rate).
Kills impl summing total calls (5+2=7 != 5).
Kills impl returning success_rate (float).
returns int; empty -> 0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_success_count,
    get_windowed_tool_success_count,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_sum_of_successes_primary_discriminator() -> None:
    """FALSIFIABLE: tool_a 3 successes (5 total) + tool_b 2 successes (2 total) -> 5.
    Kills impl summing total calls (7 != 5)."""
    _reset()
    store = _make_store(
        {
            "wgsc_a": [
                *[(_NOW - 10, 5.0, True)] * 3,
                *[(_NOW - 10, 5.0, False)] * 2,
            ],  # 3 successes, 5 total
            "wgsc_b": [(_NOW - 10, 5.0, True)] * 2,  # 2 successes, 2 total
        }
    )
    result = get_windowed_global_success_count(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, int)
    assert result == 5  # 3 + 2, not 7 (total calls), not 0.71 (rate)


def test_returns_int_not_float() -> None:
    """Return type must be int."""
    store = _make_store({"int_wgsc": [(_NOW - 10, 5.0, True)] * 3})
    assert type(get_windowed_global_success_count(_WIN, store=store, now_ms=_NOW)) is int


def test_empty_store_returns_zero() -> None:
    """No tools -> 0."""
    _reset()
    assert get_windowed_global_success_count(_WIN, store={}, now_ms=_NOW) == 0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0."""
    store = _make_store(
        {
            "wgsc_old": [(_NOW - _WIN - 100, 5.0, True)] * 3,
        }
    )
    assert get_windowed_global_success_count(_WIN, store=store, now_ms=_NOW) == 0


def test_all_failures_returns_zero() -> None:
    """All calls are failures -> 0 successes."""
    store = _make_store(
        {
            "wgsc_fail": [(_NOW - 10, 5.0, False)] * 4,
        }
    )
    assert get_windowed_global_success_count(_WIN, store=store, now_ms=_NOW) == 0


def test_consistent_with_per_tool_sum() -> None:
    """Global success count == sum of per-tool success counts."""
    _reset()
    store = _make_store(
        {
            "wgsc_x": [(_NOW - 10, 5.0, True)] * 4 + [(_NOW - 10, 5.0, False)],
            "wgsc_y": [(_NOW - 10, 5.0, True)] * 2 + [(_NOW - 10, 5.0, False)] * 3,
            "wgsc_z": [(_NOW - 10, 5.0, False)] * 2,
        }
    )
    global_count = get_windowed_global_success_count(_WIN, store=store, now_ms=_NOW)
    per_tool_sum = sum(
        get_windowed_tool_success_count(t, _WIN, store=store, now_ms=_NOW)
        for t in ("wgsc_x", "wgsc_y", "wgsc_z")
    )
    assert global_count == per_tool_sum


def test_old_successes_excluded() -> None:
    """Only recent successes counted."""
    store = _make_store(
        {
            "wgsc_mixed": [
                (_NOW - _WIN - 100, 5.0, True),  # old success, excluded
                (_NOW - 10, 5.0, True),  # recent success, counted
                (_NOW - 10, 5.0, False),  # recent failure
            ]
        }
    )
    assert get_windowed_global_success_count(_WIN, store=store, now_ms=_NOW) == 1
