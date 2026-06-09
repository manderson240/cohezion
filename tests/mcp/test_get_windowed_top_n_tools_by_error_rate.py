"""Item 964: get_windowed_top_n_tools_by_error_rate(n, window_ms, *, store=None, now_ms=None) -> list[str]
-- top-N tools by windowed error rate.

PRIMARY DISC.: 3 tools with windowed rates [0.5, 0.1, 1.0], n=2 -> [tool_1.0, tool_0.5].
Kills impl ranking by error COUNT instead of error RATE.
Kills impl returning more than n tools.
n=0 -> []; empty/no-recent -> []; returns list[str].
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_top_n_tools_by_error_rate,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_top_n_by_rate_primary_discriminator() -> None:
    """FALSIFIABLE: 3 tools rates [0.5, 0.1, 1.0], n=2 -> [tool_1.0, tool_0.5].
    Kills impl ranking by error count (tool_0.5 has more errors but lower rate than 1.0)."""
    _reset()
    store = _make_store({
        "wner_a": [(_NOW - 10, 5.0, False), (_NOW - 10, 5.0, True)],   # 1/2 errors, rate=0.5
        "wner_b": [(_NOW - 10, 5.0, True)] * 9 + [(_NOW - 10, 5.0, False)],  # 1/10, rate=0.1
        "wner_c": [(_NOW - 10, 5.0, False)],                            # 1/1 errors, rate=1.0
    })
    result = get_windowed_top_n_tools_by_error_rate(2, _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0] == "wner_c"   # rate=1.0, highest
    assert result[1] == "wner_a"   # rate=0.5, second


def test_rate_not_count_kills_count_impl() -> None:
    """Tool A: 10 errors out of 1000 calls (rate=0.01).
    Tool B: 1 error out of 2 calls (rate=0.5).
    Count-impl picks A (10>1). Rate-impl picks B (0.5>0.01)."""
    _reset()
    store = _make_store({
        "wner_count_winner": [
            *[(_NOW - 10, 5.0, False)] * 10,
            *[(_NOW - 10, 5.0, True)] * 990,
        ],  # 10/1000, rate=0.01
        "wner_rate_winner": [
            (_NOW - 10, 5.0, False),
            (_NOW - 10, 5.0, True),
        ],  # 1/2, rate=0.5
    })
    result = get_windowed_top_n_tools_by_error_rate(1, _WIN, store=store, now_ms=_NOW)
    assert result == ["wner_rate_winner"]   # rate 0.5 > 0.01


def test_only_windowed_calls_used() -> None:
    """Kills cumulative impl: old errors outside window don't affect ranking."""
    _reset()
    store = _make_store({
        "wner_old_errors": [(_NOW - _WIN - 100, 5.0, False)] * 5,  # 5 old errors, 0 recent
        "wner_fresh_error": [(_NOW - 10, 5.0, False)],             # 1 recent error, rate=1.0
    })
    result = get_windowed_top_n_tools_by_error_rate(2, _WIN, store=store, now_ms=_NOW)
    assert "wner_fresh_error" in result
    assert "wner_old_errors" not in result


def test_empty_store_returns_empty_list() -> None:
    """No tools -> []."""
    _reset()
    assert get_windowed_top_n_tools_by_error_rate(5, _WIN, store={}, now_ms=_NOW) == []


def test_no_recent_calls_returns_empty_list() -> None:
    """All calls outside window -> []."""
    store = _make_store({
        "wner_stale": [(_NOW - _WIN - 100, 5.0, False)] * 3,
    })
    assert get_windowed_top_n_tools_by_error_rate(3, _WIN, store=store, now_ms=_NOW) == []


def test_n_zero_returns_empty_list() -> None:
    """n=0 -> []."""
    store = _make_store({"wner_any": [(_NOW - 10, 5.0, False)] * 2})
    assert get_windowed_top_n_tools_by_error_rate(0, _WIN, store=store, now_ms=_NOW) == []


def test_n_greater_than_active_returns_all() -> None:
    """n > active tools -> all active tools returned (no padding)."""
    store = _make_store({
        "wner_x": [(_NOW - 10, 5.0, False)],    # rate=1.0
        "wner_y": [(_NOW - 10, 5.0, True)],     # rate=0.0
    })
    result = get_windowed_top_n_tools_by_error_rate(10, _WIN, store=store, now_ms=_NOW)
    assert len(result) == 2
    assert set(result) == {"wner_x", "wner_y"}


def test_ties_broken_alphabetically() -> None:
    """Equal error rates -> alphabetical ordering."""
    store = _make_store({
        "wner_zzz": [(_NOW - 10, 5.0, False)],  # rate=1.0
        "wner_aaa": [(_NOW - 10, 5.0, False)],  # rate=1.0
        "wner_mmm": [(_NOW - 10, 5.0, False)],  # rate=1.0
    })
    result = get_windowed_top_n_tools_by_error_rate(3, _WIN, store=store, now_ms=_NOW)
    assert result == ["wner_aaa", "wner_mmm", "wner_zzz"]


def test_returns_list_type() -> None:
    """Return type is always list."""
    store = _make_store({"rtype_wner": [(_NOW - 10, 5.0, False)]})
    assert isinstance(
        get_windowed_top_n_tools_by_error_rate(1, _WIN, store=store, now_ms=_NOW), list
    )


def test_all_successful_tools_included_at_rate_zero() -> None:
    """Tools with 0 errors have rate=0.0 and are still valid active tools."""
    store = _make_store({
        "wner_ok_a": [(_NOW - 10, 5.0, True)] * 3,   # rate=0.0
        "wner_ok_b": [(_NOW - 10, 5.0, True)] * 2,   # rate=0.0
    })
    result = get_windowed_top_n_tools_by_error_rate(2, _WIN, store=store, now_ms=_NOW)
    assert len(result) == 2
    # All tied at 0.0, so alphabetical
    assert result == ["wner_ok_a", "wner_ok_b"]
