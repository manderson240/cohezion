"""Item 973: get_windowed_global_error_count(window_ms, *, store=None, now_ms=None) -> int
-- total failed calls fleet-wide in window.

PRIMARY DISC.: tool_a 2 errors + tool_b 3 errors -> 5 (not total calls, not rate).
Kills impl summing total calls.
Kills impl returning global_error_rate (float).
returns int; global_success_count + global_error_count == global_call_count.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_error_count,
    get_windowed_global_success_count,
    get_windowed_global_call_count,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_sum_of_errors_primary_discriminator() -> None:
    """FALSIFIABLE: tool_a 2 errors (5 total) + tool_b 3 errors (3 total) -> 5.
    Kills impl summing total calls (8 != 5)."""
    _reset()
    store = _make_store(
        {
            "wgec_a": [
                *[(_NOW - 10, 5.0, True)] * 3,
                *[(_NOW - 10, 5.0, False)] * 2,
            ],  # 2 errors, 5 total
            "wgec_b": [(_NOW - 10, 5.0, False)] * 3,  # 3 errors, 3 total
        }
    )
    result = get_windowed_global_error_count(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, int)
    assert result == 5  # 2 + 3, not 8 (total calls)


def test_returns_int_not_float() -> None:
    """Return type must be int."""
    store = _make_store({"int_wgec": [(_NOW - 10, 5.0, False)] * 2})
    assert type(get_windowed_global_error_count(_WIN, store=store, now_ms=_NOW)) is int


def test_empty_store_returns_zero() -> None:
    """No tools -> 0."""
    _reset()
    assert get_windowed_global_error_count(_WIN, store={}, now_ms=_NOW) == 0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0."""
    store = _make_store(
        {
            "wgec_old": [(_NOW - _WIN - 100, 5.0, False)] * 3,
        }
    )
    assert get_windowed_global_error_count(_WIN, store=store, now_ms=_NOW) == 0


def test_all_successful_returns_zero() -> None:
    """No failures -> 0 errors."""
    store = _make_store(
        {
            "wgec_ok": [(_NOW - 10, 5.0, True)] * 5,
        }
    )
    assert get_windowed_global_error_count(_WIN, store=store, now_ms=_NOW) == 0


def test_success_plus_error_equals_total() -> None:
    """Consistency: success_count + error_count == global_call_count."""
    _reset()
    store = _make_store(
        {
            "wgec_x": [(_NOW - 10, 5.0, True)] * 4 + [(_NOW - 10, 5.0, False)] * 2,
            "wgec_y": [(_NOW - 10, 5.0, False)] * 3,
        }
    )
    errors = get_windowed_global_error_count(_WIN, store=store, now_ms=_NOW)
    successes = get_windowed_global_success_count(_WIN, store=store, now_ms=_NOW)
    total = get_windowed_global_call_count(_WIN, store=store, now_ms=_NOW)
    assert errors + successes == total


def test_old_errors_excluded() -> None:
    """Old failures outside window don't count."""
    store = _make_store(
        {
            "wgec_mixed": [
                (_NOW - _WIN - 100, 5.0, False),  # old error, excluded
                (_NOW - 10, 5.0, False),  # recent error, counted
                (_NOW - 10, 5.0, True),  # recent success
            ]
        }
    )
    assert get_windowed_global_error_count(_WIN, store=store, now_ms=_NOW) == 1
