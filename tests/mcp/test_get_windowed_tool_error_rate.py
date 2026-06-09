"""Item 985: get_windowed_tool_error_rate(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- windowed per-tool error rate standalone.

PRIMARY DISC.: 5 calls with 2 failures -> error_rate=0.4
(not error_count=2; not success_rate=0.6; not success_count=3).
0.0 for unknown/no-recent-calls; consistent with telemetry_full["error_rate"]; returns float.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_error_rate,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_error_rate_primary_discriminator() -> None:
    """FALSIFIABLE: 3 successes + 2 failures -> error_rate=0.4 (not 2, not 0.6, not 3)."""
    _reset()
    store = _make_store({
        "wer_a": [
            (_NOW - 10, 10.0, True),
            (_NOW - 10, 20.0, True),
            (_NOW - 10, 30.0, True),
            (_NOW - 10, 40.0, False),
            (_NOW - 10, 50.0, False),
        ]
    })
    result = get_windowed_tool_error_rate("wer_a", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 0.4) < 0.001   # not error_count=2, not success_rate=0.6, not success_count=3


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_error_rate("no_such_wer", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    store = _make_store({
        "wer_old": [(_NOW - _WIN - 100, 50.0, False)] * 3,
    })
    assert get_windowed_tool_error_rate("wer_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_all_success_returns_zero() -> None:
    """All successful -> error_rate=0.0."""
    store = _make_store({
        "wer_ok": [(_NOW - 10, 10.0, True)] * 5,
    })
    assert abs(get_windowed_tool_error_rate("wer_ok", _WIN, store=store, now_ms=_NOW)) < 0.001


def test_all_failure_returns_one() -> None:
    """All failed -> error_rate=1.0."""
    store = _make_store({
        "wer_fail": [(_NOW - 10, 10.0, False)] * 3,
    })
    assert abs(get_windowed_tool_error_rate("wer_fail", _WIN, store=store, now_ms=_NOW) - 1.0) < 0.001


def test_consistent_with_telemetry_full() -> None:
    """error_rate == get_windowed_tool_telemetry_full()['error_rate']."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_tool_telemetry_full
    store = _make_store({
        "wer_full": [
            (_NOW - 10, float(v), v % 3 != 0) for v in range(1, 10)
        ]
    })
    standalone = get_windowed_tool_error_rate("wer_full", _WIN, store=store, now_ms=_NOW)
    from_full = get_windowed_tool_telemetry_full("wer_full", _WIN, store=store, now_ms=_NOW)["error_rate"]
    assert abs(standalone - from_full) < 0.001


def test_returns_float_type() -> None:
    """Return type is float."""
    store = _make_store({
        "rtype_wer": [(_NOW - 10, 10.0, True)] * 3 + [(_NOW - 10, 10.0, False)] * 1,
    })
    result = get_windowed_tool_error_rate("rtype_wer", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)


def test_error_rate_plus_success_rate_equals_one() -> None:
    """error_rate + success_rate == 1.0 for non-empty window."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_tool_telemetry_full
    store = _make_store({
        "wer_sum": [(_NOW - 10, 10.0, True)] * 4 + [(_NOW - 10, 20.0, False)] * 1,
    })
    er = get_windowed_tool_error_rate("wer_sum", _WIN, store=store, now_ms=_NOW)
    sr = get_windowed_tool_telemetry_full("wer_sum", _WIN, store=store, now_ms=_NOW)["success_rate"]
    assert abs(er + sr - 1.0) < 0.001
