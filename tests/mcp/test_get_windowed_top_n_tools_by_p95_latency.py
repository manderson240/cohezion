"""Item 965: get_windowed_top_n_tools_by_p95_latency(n, window_ms, *, store=None, now_ms=None) -> list[str]
-- top-N slowest tools by windowed p95 latency.

PRIMARY DISC.: 3 tools with windowed p95 values [10, 50, 100], n=2 -> [tool_100, tool_50].
Kills impl ranking by p50 instead of p95.
Kills impl returning more than n tools.
n=0 -> []; empty/no-recent -> []; returns list[str].
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_top_n_tools_by_p95_latency,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_top_n_by_p95_primary_discriminator() -> None:
    """FALSIFIABLE: 3 tools p95=[10,50,100], n=2 -> [tool_100, tool_50].
    Kills impl ranking by p50 (p50 ordering could differ from p95 ordering)."""
    _reset()
    # tool_a: all lats 10 -> p95=10, p50=10
    # tool_b: all lats 50 -> p95=50, p50=50
    # tool_c: all lats 100 -> p95=100, p50=100
    store = _make_store({
        "wnp_a": [(_NOW - 10, 10.0, True)] * 5,
        "wnp_b": [(_NOW - 10, 50.0, True)] * 5,
        "wnp_c": [(_NOW - 10, 100.0, True)] * 5,
    })
    result = get_windowed_top_n_tools_by_p95_latency(2, _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0] == "wnp_c"   # p95=100, highest
    assert result[1] == "wnp_b"   # p95=50, second


def test_p95_not_p50_discriminator() -> None:
    """Kills impl using p50 instead of p95.
    Tool A: lats=[1,1,1,1,100] -> p50=1, p95=100.
    Tool B: lats=[50,50,50,50,50] -> p50=50, p95=50.
    By p50: B wins (50>1). By p95: A wins (100>50)."""
    _reset()
    store = _make_store({
        "wnp_p95_winner": [
            (_NOW - 10, 1.0, True),
            (_NOW - 10, 1.0, True),
            (_NOW - 10, 1.0, True),
            (_NOW - 10, 1.0, True),
            (_NOW - 10, 100.0, True),
        ],  # p50=1, p95=100
        "wnp_p50_winner": [(_NOW - 10, 50.0, True)] * 5,  # p50=50, p95=50
    })
    result = get_windowed_top_n_tools_by_p95_latency(1, _WIN, store=store, now_ms=_NOW)
    assert result == ["wnp_p95_winner"]   # p95=100 > p95=50


def test_only_windowed_calls_used() -> None:
    """Kills cumulative impl: old high-latency calls outside window don't affect ranking."""
    _reset()
    store = _make_store({
        "wnp_stale": [(_NOW - _WIN - 100, 9999.0, True)] * 5,  # old 9999ms calls, none recent
        "wnp_fresh": [(_NOW - 10, 1.0, True)] * 5,             # recent 1ms calls
    })
    result = get_windowed_top_n_tools_by_p95_latency(2, _WIN, store=store, now_ms=_NOW)
    assert "wnp_fresh" in result
    assert "wnp_stale" not in result


def test_empty_store_returns_empty_list() -> None:
    """No tools -> []."""
    _reset()
    assert get_windowed_top_n_tools_by_p95_latency(3, _WIN, store={}, now_ms=_NOW) == []


def test_no_recent_calls_returns_empty_list() -> None:
    """All calls outside window -> []."""
    store = _make_store({
        "wnp_old": [(_NOW - _WIN - 100, 50.0, True)] * 3,
    })
    assert get_windowed_top_n_tools_by_p95_latency(3, _WIN, store=store, now_ms=_NOW) == []


def test_n_zero_returns_empty_list() -> None:
    """n=0 -> []."""
    store = _make_store({"wnp_any": [(_NOW - 10, 5.0, True)] * 3})
    assert get_windowed_top_n_tools_by_p95_latency(0, _WIN, store=store, now_ms=_NOW) == []


def test_n_greater_than_active_returns_all() -> None:
    """n > active tools -> all active tools returned."""
    store = _make_store({
        "wnp_x": [(_NOW - 10, 10.0, True)],
        "wnp_y": [(_NOW - 10, 20.0, True)],
    })
    result = get_windowed_top_n_tools_by_p95_latency(10, _WIN, store=store, now_ms=_NOW)
    assert len(result) == 2
    assert set(result) == {"wnp_x", "wnp_y"}


def test_ties_broken_alphabetically() -> None:
    """Equal p95 -> alphabetical ordering."""
    store = _make_store({
        "wnp_zzz": [(_NOW - 10, 50.0, True)] * 3,
        "wnp_aaa": [(_NOW - 10, 50.0, True)] * 3,
        "wnp_mmm": [(_NOW - 10, 50.0, True)] * 3,
    })
    result = get_windowed_top_n_tools_by_p95_latency(3, _WIN, store=store, now_ms=_NOW)
    assert result == ["wnp_aaa", "wnp_mmm", "wnp_zzz"]


def test_returns_list_type() -> None:
    """Return type is always list."""
    store = _make_store({"rtype_wnp": [(_NOW - 10, 5.0, True)]})
    assert isinstance(
        get_windowed_top_n_tools_by_p95_latency(1, _WIN, store=store, now_ms=_NOW), list
    )
