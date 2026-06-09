"""Item 963: get_windowed_top_n_tools_by_call_count(n, window_ms, *, store=None, now_ms=None) -> list[str]
-- top-N tools by windowed call count.

PRIMARY DISC.: 4 tools with windowed counts [5,1,3,2], n=2 -> exactly [tool5, tool3].
Kills impl returning cumulative counts (old calls outside window must be ignored).
Kills impl returning more than n tools.
n > active tools -> all active tools (no padding); empty -> [].
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_top_n_tools_by_call_count,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_top_n_primary_discriminator() -> None:
    """FALSIFIABLE: 4 tools windowed counts [5,1,3,2], n=2 -> [tool5, tool3].
    Kills cumulative impl (old calls outside window must be ignored).
    Kills impl returning more than n tools."""
    _reset()
    store = _make_store({
        "wnc_a": [(_NOW - 10, 5.0, True)] * 5,    # 5 in window
        "wnc_b": [(_NOW - 10, 5.0, True)] * 1,    # 1 in window
        "wnc_c": [(_NOW - 10, 5.0, True)] * 3,    # 3 in window
        "wnc_d": [(_NOW - 10, 5.0, True)] * 2,    # 2 in window
    })
    result = get_windowed_top_n_tools_by_call_count(2, _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0] == "wnc_a"   # count=5, highest
    assert result[1] == "wnc_c"   # count=3, second


def test_windowed_not_cumulative_kills_stale_tool() -> None:
    """Kills cumulative impl: tool with 100 old calls + 0 recent should not appear.
    Tool with 1 recent call should outrank it."""
    _reset()
    store = _make_store({
        "wnc_stale": [(_NOW - _WIN - 100, 5.0, True)] * 100,  # 100 old calls, 0 in window
        "wnc_fresh": [(_NOW - 10, 5.0, True)] * 1,            # 1 recent call
    })
    result = get_windowed_top_n_tools_by_call_count(2, _WIN, store=store, now_ms=_NOW)
    assert "wnc_fresh" in result
    assert "wnc_stale" not in result   # no recent calls => excluded


def test_n_greater_than_active_tools_returns_all_active() -> None:
    """n > active tools -> returns all active tools (no padding)."""
    store = _make_store({
        "wnc_x": [(_NOW - 10, 5.0, True)] * 2,
        "wnc_y": [(_NOW - 10, 5.0, True)] * 4,
    })
    result = get_windowed_top_n_tools_by_call_count(10, _WIN, store=store, now_ms=_NOW)
    assert len(result) == 2
    assert set(result) == {"wnc_x", "wnc_y"}


def test_empty_store_returns_empty_list() -> None:
    """No tools -> []."""
    _reset()
    assert get_windowed_top_n_tools_by_call_count(5, _WIN, store={}, now_ms=_NOW) == []


def test_no_recent_calls_returns_empty_list() -> None:
    """All calls outside window -> []."""
    store = _make_store({
        "wnc_old": [(_NOW - _WIN - 100, 5.0, True)] * 3,
    })
    assert get_windowed_top_n_tools_by_call_count(3, _WIN, store=store, now_ms=_NOW) == []


def test_returns_list_type() -> None:
    """Return type is always list."""
    store = _make_store({"rtype_wnc": [(_NOW - 10, 5.0, True)]})
    assert isinstance(get_windowed_top_n_tools_by_call_count(1, _WIN, store=store, now_ms=_NOW), list)


def test_descending_order() -> None:
    """Result is sorted descending by count (highest first)."""
    store = _make_store({
        "desc_b": [(_NOW - 10, 5.0, True)] * 1,
        "desc_c": [(_NOW - 10, 5.0, True)] * 5,
        "desc_a": [(_NOW - 10, 5.0, True)] * 3,
    })
    result = get_windowed_top_n_tools_by_call_count(3, _WIN, store=store, now_ms=_NOW)
    assert result[0] == "desc_c"   # 5
    assert result[1] == "desc_a"   # 3
    assert result[2] == "desc_b"   # 1


def test_ties_broken_alphabetically() -> None:
    """Tied counts -> alphabetical order within the tie group."""
    store = _make_store({
        "wnc_zzz": [(_NOW - 10, 5.0, True)] * 3,
        "wnc_aaa": [(_NOW - 10, 5.0, True)] * 3,
        "wnc_mmm": [(_NOW - 10, 5.0, True)] * 3,
    })
    result = get_windowed_top_n_tools_by_call_count(3, _WIN, store=store, now_ms=_NOW)
    assert result == ["wnc_aaa", "wnc_mmm", "wnc_zzz"]


def test_n_zero_returns_empty_list() -> None:
    """n=0 -> []."""
    store = _make_store({"wnc_any": [(_NOW - 10, 5.0, True)] * 3})
    assert get_windowed_top_n_tools_by_call_count(0, _WIN, store=store, now_ms=_NOW) == []


def test_single_tool_n_one() -> None:
    """1 tool, n=1 -> list of length 1."""
    store = _make_store({"wnc_single": [(_NOW - 10, 5.0, True)] * 4})
    result = get_windowed_top_n_tools_by_call_count(1, _WIN, store=store, now_ms=_NOW)
    assert result == ["wnc_single"]
