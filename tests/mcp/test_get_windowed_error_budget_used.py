"""Item 966: get_windowed_error_budget_used(tool_name, budget_rate, window_ms, *, store=None, now_ms=None) -> float
-- fraction of error budget consumed (actual_error_rate / budget_rate).

PRIMARY DISC.: tool with 2/10 errors (rate=0.2), budget_rate=0.05 -> 4.0 (not 0.2!).
Kills impl returning raw error rate instead of ratio.
Kills impl clamping at 1.0 (over-budget must be >1.0).
0 recent calls -> 0.0; budget_rate=0 -> 0.0; returns float.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_error_budget_used,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_ratio_not_rate_primary_discriminator() -> None:
    """FALSIFIABLE: 2/10 errors (rate=0.2), budget_rate=0.05 -> 4.0 (not 0.2).
    Kills impl returning raw error rate (0.2 != 4.0)."""
    _reset()
    store = _make_store({
        "ebu_a": [
            *[(_NOW - 10, 5.0, False)] * 2,
            *[(_NOW - 10, 5.0, True)] * 8,
        ]
    })
    result = get_windowed_error_budget_used("ebu_a", 0.05, _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 4.0) < 0.001   # 0.2 / 0.05 = 4.0, NOT 0.2


def test_over_budget_exceeds_one() -> None:
    """Kills impl clamping at 1.0: over-budget must return value > 1.0."""
    _reset()
    store = _make_store({
        "ebu_over": [(_NOW - 10, 5.0, False)] * 5 + [(_NOW - 10, 5.0, True)] * 5,
    })  # rate=0.5, budget=0.1 -> ratio=5.0
    result = get_windowed_error_budget_used("ebu_over", 0.1, _WIN, store=store, now_ms=_NOW)
    assert result > 1.0
    assert abs(result - 5.0) < 0.001


def test_under_budget_is_less_than_one() -> None:
    """Under budget: actual_rate < budget_rate -> ratio < 1.0."""
    store = _make_store({
        "ebu_under": [(_NOW - 10, 5.0, False)] + [(_NOW - 10, 5.0, True)] * 9,
    })  # rate=0.1, budget=0.5 -> ratio=0.2
    result = get_windowed_error_budget_used("ebu_under", 0.5, _WIN, store=store, now_ms=_NOW)
    assert 0.0 < result < 1.0
    assert abs(result - 0.2) < 0.001


def test_no_recent_calls_returns_zero() -> None:
    """No recent calls -> 0.0."""
    store = _make_store({
        "ebu_old": [(_NOW - _WIN - 100, 5.0, False)] * 3,
    })
    result = get_windowed_error_budget_used("ebu_old", 0.1, _WIN, store=store, now_ms=_NOW)
    assert result == 0.0


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    result = get_windowed_error_budget_used("no_such_ebu", 0.1, _WIN, store={}, now_ms=_NOW)
    assert result == 0.0


def test_budget_rate_zero_returns_zero() -> None:
    """budget_rate=0 -> 0.0 (avoid division by zero)."""
    store = _make_store({"ebu_zero": [(_NOW - 10, 5.0, False)]})
    result = get_windowed_error_budget_used("ebu_zero", 0.0, _WIN, store=store, now_ms=_NOW)
    assert result == 0.0


def test_all_successful_tool_within_budget() -> None:
    """All successful -> error_rate=0.0 -> budget_used=0.0."""
    store = _make_store({"ebu_ok": [(_NOW - 10, 5.0, True)] * 5})
    result = get_windowed_error_budget_used("ebu_ok", 0.1, _WIN, store=store, now_ms=_NOW)
    assert result == 0.0


def test_all_failed_tool_over_budget() -> None:
    """All failed -> error_rate=1.0 -> budget_used = 1/budget_rate."""
    store = _make_store({"ebu_all_fail": [(_NOW - 10, 5.0, False)] * 5})
    result = get_windowed_error_budget_used("ebu_all_fail", 0.25, _WIN, store=store, now_ms=_NOW)
    assert abs(result - 4.0) < 0.001   # 1.0 / 0.25 = 4.0


def test_returns_float_type() -> None:
    """Return type is float."""
    store = _make_store({"rtype_ebu": [(_NOW - 10, 5.0, False)]})
    assert isinstance(
        get_windowed_error_budget_used("rtype_ebu", 0.1, _WIN, store=store, now_ms=_NOW), float
    )
