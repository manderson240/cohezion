"""Item 958: get_windowed_slowest_tool(window_ms, *, store=None, now_ms=None) -> str | None
-- tool with the highest windowed p95 latency.

PRIMARY DISC.: 3 tools with windowed p95s [10, 500, 100]ms -> tool with p95=500 wins.
Kills impl returning alphabetically first tool regardless of p95.
Kills impl computing cumulative p95 instead of windowed p95.
Ties broken alphabetically. None when empty. Returns str | None.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_slowest_tool,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_highest_windowed_p95_wins_primary_discriminator() -> None:
    """FALSIFIABLE: tool a=10ms p95, tool b=500ms p95, tool c=100ms p95.
    'b' has the highest p95 -> b wins.
    Kills impl returning alphabetically first; kills cumulative-p95 impl."""
    _reset()
    store = _make_store(
        {
            "wsl_a": [(_NOW - 10, 10.0, True)],  # p95 = 10.0
            "wsl_b": [(_NOW - 10, 500.0, True)],  # p95 = 500.0  (slowest)
            "wsl_c": [(_NOW - 10, 100.0, True)],  # p95 = 100.0
        }
    )
    result = get_windowed_slowest_tool(_WIN, store=store, now_ms=_NOW)
    assert result == "wsl_b"
    assert result != "wsl_a"  # alphabetically first but fastest


def test_empty_store_returns_none() -> None:
    """No tools -> None."""
    _reset()
    assert get_windowed_slowest_tool(_WIN, store={}, now_ms=_NOW) is None


def test_no_recent_calls_returns_none() -> None:
    """All calls outside window -> None."""
    store = _make_store(
        {
            "wsl_old": [(_NOW - _WIN - 100, 500.0, True)],
        }
    )
    assert get_windowed_slowest_tool(_WIN, store=store, now_ms=_NOW) is None


def test_tie_broken_alphabetically() -> None:
    """Two tools with equal windowed p95 -> alphabetically first wins."""
    store = _make_store(
        {
            "zzz_slow": [(_NOW - 10, 100.0, True)],
            "aaa_slow": [(_NOW - 10, 100.0, True)],
        }
    )
    result = get_windowed_slowest_tool(_WIN, store=store, now_ms=_NOW)
    assert result == "aaa_slow"


def test_single_tool_returns_that_tool() -> None:
    """Single tool with recent calls -> that tool."""
    store = _make_store(
        {
            "only_wsl": [(_NOW - 10, 42.0, True)],
        }
    )
    assert get_windowed_slowest_tool(_WIN, store=store, now_ms=_NOW) == "only_wsl"


def test_old_calls_not_considered() -> None:
    """Tool with many old slow calls and few recent fast calls -> recent fast calls count."""
    store = _make_store(
        {
            "wsl_old_slow": [
                (_NOW - _WIN - 10, 9999.0, True),  # old slow -- ignored
                (_NOW - 10, 5.0, True),  # recent fast
            ],
            "wsl_recent_fast": [(_NOW - 10, 200.0, True)],  # recent slow
        }
    )
    result = get_windowed_slowest_tool(_WIN, store=store, now_ms=_NOW)
    # wsl_old_slow has recent p95=5; wsl_recent_fast has recent p95=200
    assert result == "wsl_recent_fast"
