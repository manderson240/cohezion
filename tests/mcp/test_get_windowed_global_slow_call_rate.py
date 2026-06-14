"""Item 1006: get_windowed_global_slow_call_rate(window_ms, threshold_ms, *, store=None, now_ms=None) -> float
-- fleet-wide SLO violation rate (fraction of calls exceeding threshold).

slow_call_count_all_tools / total_call_count_all_tools. Returns float in [0, 1].
0.0 when no recent calls. Strictly > threshold. Pools ALL tools.

PRIMARY DISC.: tool_a [10, 200] + tool_b [300, 50] threshold=100 -> 0.5
  (2 slow [200, 300] / 4 total = 0.5; kills slow_count=2 int; kills total=4 int).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_slow_call_rate,
    get_windowed_global_slow_call_count,
    get_windowed_tool_slow_call_rate,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_slow_rate_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a[10,200] + tool_b[300,50] threshold=100 -> 0.5.

    2 slow [200, 300] / 4 total = 0.5.
    Kills impl returning slow_count=2 (int).
    Kills impl returning total_count=4 (int).
    """
    _reset()
    store = _make_store(
        {
            "gsr_a": [(_NOW - 10, 10.0, True), (_NOW - 10, 200.0, True)],
            "gsr_b": [(_NOW - 10, 300.0, True), (_NOW - 10, 50.0, True)],
        }
    )
    result = get_windowed_global_slow_call_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 0.5) < 1e-9, f"2/4=0.5; kills count=2 or total=4; got {result}"


def test_single_tool_matches_per_tool_rate() -> None:
    """With one tool, global rate == per-tool rate."""
    _reset()
    store = _make_store(
        {
            "gsr_one": [(_NOW - 10, float(v), True) for v in [10, 50, 200, 300]],
        }
    )
    global_rate = get_windowed_global_slow_call_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    per_tool = get_windowed_tool_slow_call_rate("gsr_one", _WIN, 100.0, store=store, now_ms=_NOW)
    assert abs(global_rate - per_tool) < 1e-9, (
        f"single tool: global_rate={global_rate} must equal per_tool={per_tool}"
    )


def test_consistent_with_slow_count_over_total() -> None:
    """rate == global_slow_count / total_count (cross-function consistency)."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_global_call_count

    _reset()
    store = _make_store(
        {
            "gsr_cons_a": [(_NOW - 10, float(v), True) for v in [10, 200, 400]],
            "gsr_cons_b": [(_NOW - 10, float(v), True) for v in [50, 300]],
        }
    )
    rate = get_windowed_global_slow_call_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    slow = get_windowed_global_slow_call_count(_WIN, 100.0, store=store, now_ms=_NOW)
    total = get_windowed_global_call_count(_WIN, store=store, now_ms=_NOW)
    assert abs(rate - slow / total) < 1e-9, (
        f"rate={rate} must equal slow/total={slow}/{total}={slow / total}"
    )


def test_all_slow_rate_is_one() -> None:
    """All calls slow -> rate=1.0."""
    _reset()
    store = _make_store(
        {
            "gsr_all_a": [(_NOW - 10, 200.0, True)],
            "gsr_all_b": [(_NOW - 10, 300.0, True)],
        }
    )
    result = get_windowed_global_slow_call_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"All slow -> 1.0; got {result}"


def test_no_slow_calls_rate_is_zero() -> None:
    """No slow calls -> rate=0.0."""
    _reset()
    store = _make_store(
        {
            "gsr_none_a": [(_NOW - 10, 10.0, True)],
            "gsr_none_b": [(_NOW - 10, 20.0, True)],
        }
    )
    result = get_windowed_global_slow_call_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    assert abs(result - 0.0) < 1e-9, f"No slow calls -> 0.0; got {result}"


def test_empty_store_returns_zero() -> None:
    _reset()
    assert get_windowed_global_slow_call_rate(_WIN, 100.0, store={}, now_ms=_NOW) == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"gsr_rt": [(_NOW - 10, 200.0, True)] * 3})
    assert isinstance(
        get_windowed_global_slow_call_rate(_WIN, 100.0, store=store, now_ms=_NOW), float
    )
