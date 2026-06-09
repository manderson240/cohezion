"""Item 967: get_windowed_tools_over_error_budget(budget_rate, window_ms, *, store=None, now_ms=None) -> list[str]
-- sorted list of tools with windowed error rate strictly > budget_rate.

PRIMARY DISC.: 3 tools rates [0.5, 0.1, 0.2], budget_rate=0.15 -> sorted([tool_0.5, tool_0.2]).
Kills impl returning all active tools regardless of budget.
Kills impl comparing absolute error count vs budget_rate.
budget_rate=0 -> all tools with any error; empty/no-errors -> []; returns list[str].
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tools_over_error_budget,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_over_budget_primary_discriminator() -> None:
    """FALSIFIABLE: 3 tools rates [0.5, 0.1, 0.2], budget=0.15 -> [tool_0.2, tool_0.5].
    Kills impl returning all tools (tool_0.1 must be excluded)."""
    _reset()
    store = _make_store({
        "wob_a": [(_NOW - 10, 5.0, False)] + [(_NOW - 10, 5.0, True)],        # rate=0.5
        "wob_b": [(_NOW - 10, 5.0, False)] + [(_NOW - 10, 5.0, True)] * 9,    # rate=0.1
        "wob_c": [(_NOW - 10, 5.0, False)] * 2 + [(_NOW - 10, 5.0, True)] * 8,  # rate=0.2
    })
    result = get_windowed_tools_over_error_budget(0.15, _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, list)
    assert "wob_a" in result    # rate=0.5 > 0.15
    assert "wob_c" in result    # rate=0.2 > 0.15
    assert "wob_b" not in result  # rate=0.1 <= 0.15
    assert result == sorted(result)   # alphabetical


def test_at_budget_boundary_not_included() -> None:
    """Strict >: a tool with error_rate == budget_rate is NOT included."""
    store = _make_store({
        "wob_exact": [(_NOW - 10, 5.0, False)] + [(_NOW - 10, 5.0, True)] * 3,  # rate=0.25
    })
    result = get_windowed_tools_over_error_budget(0.25, _WIN, store=store, now_ms=_NOW)
    assert "wob_exact" not in result   # exactly at budget, not over


def test_budget_rate_zero_returns_tools_with_any_error() -> None:
    """budget_rate=0 -> all active tools with >=1 error (rate > 0 > 0.0)."""
    store = _make_store({
        "wob_some_err": [(_NOW - 10, 5.0, False)] + [(_NOW - 10, 5.0, True)] * 4,  # rate=0.2
        "wob_all_ok": [(_NOW - 10, 5.0, True)] * 5,  # rate=0.0, NOT over
    })
    result = get_windowed_tools_over_error_budget(0.0, _WIN, store=store, now_ms=_NOW)
    assert "wob_some_err" in result
    assert "wob_all_ok" not in result


def test_all_under_budget_returns_empty() -> None:
    """All tools at or below budget -> []."""
    store = _make_store({
        "wob_low": [(_NOW - 10, 5.0, False)] + [(_NOW - 10, 5.0, True)] * 9,  # rate=0.1
    })
    result = get_windowed_tools_over_error_budget(0.5, _WIN, store=store, now_ms=_NOW)
    assert result == []


def test_empty_store_returns_empty() -> None:
    """No tools -> []."""
    _reset()
    assert get_windowed_tools_over_error_budget(0.1, _WIN, store={}, now_ms=_NOW) == []


def test_no_recent_calls_returns_empty() -> None:
    """All calls outside window -> []."""
    store = _make_store({
        "wob_old": [(_NOW - _WIN - 100, 5.0, False)] * 3,
    })
    assert get_windowed_tools_over_error_budget(0.1, _WIN, store=store, now_ms=_NOW) == []


def test_result_is_sorted_alphabetically() -> None:
    """Result is always alphabetically sorted."""
    store = _make_store({
        "wob_zzz": [(_NOW - 10, 5.0, False)],   # rate=1.0
        "wob_aaa": [(_NOW - 10, 5.0, False)],   # rate=1.0
        "wob_mmm": [(_NOW - 10, 5.0, False)],   # rate=1.0
    })
    result = get_windowed_tools_over_error_budget(0.5, _WIN, store=store, now_ms=_NOW)
    assert result == ["wob_aaa", "wob_mmm", "wob_zzz"]


def test_returns_list_type() -> None:
    """Return type is always list."""
    store = _make_store({"rtype_wob": [(_NOW - 10, 5.0, False)]})
    assert isinstance(
        get_windowed_tools_over_error_budget(0.0, _WIN, store=store, now_ms=_NOW), list
    )
