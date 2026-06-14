"""Item 931: get_windowed_tool_count(window_ms, *, now_ms=None) -> int --
number of distinct tools active in window.

PRIMARY DISC.: 2 active + 1 stale -> 2
(kills impl counting all windowed tools or total call count).
empty -> 0; injectable store; returns int.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    record_tool_call_windowed,
    get_windowed_tool_count,
)

_BIG_WINDOW = 60_000.0  # 60 seconds — effectively "all recent"
_SMALL_WINDOW = 1_000.0  # 1 second


def _reset():
    clear_telemetry_stores()


def test_active_vs_stale_primary_discriminator() -> None:
    """FALSIFIABLE: 2 active tools + 1 stale -> 2 (NOT 3).
    Kills impl returning all windowed tool names ignoring timestamps."""
    _reset()
    now = 100_000.0
    # active: recorded within 1s window
    record_tool_call_windowed("active_a", 10.0, True, ts_ms=99_500.0)
    record_tool_call_windowed("active_b", 15.0, True, ts_ms=99_800.0)
    # stale: recorded 2 seconds before now — outside 1s window
    record_tool_call_windowed("stale_c", 20.0, True, ts_ms=97_000.0)
    result = get_windowed_tool_count(_SMALL_WINDOW, now_ms=now)
    assert result == 2  # NOT 3


def test_empty_store_returns_zero() -> None:
    """Empty store -> 0."""
    _reset()
    store: dict = {}
    result = get_windowed_tool_count(_BIG_WINDOW, store=store, now_ms=0.0)
    assert result == 0


def test_returns_int() -> None:
    """Return type is int."""
    _reset()
    now = 10_000.0
    record_tool_call_windowed("type_tool", 5.0, True, ts_ms=9_000.0)
    result = get_windowed_tool_count(_BIG_WINDOW, now_ms=now)
    assert isinstance(result, int)


def test_multiple_calls_one_tool_counts_one() -> None:
    """5 calls to 1 tool -> count=1 (distinct, not total calls)."""
    _reset()
    now = 10_000.0
    for _ in range(5):
        record_tool_call_windowed("busy_tool", 5.0, True, ts_ms=9_500.0)
    assert get_windowed_tool_count(_BIG_WINDOW, now_ms=now) == 1


def test_injectable_store() -> None:
    """Injectable store isolation — uses provided store, not module global."""
    _reset()
    now = 10_000.0
    custom: dict = {
        "injected_a": [(9_000.0, 5.0, True)],
        "injected_b": [(9_500.0, 8.0, True)],
    }
    result = get_windowed_tool_count(_BIG_WINDOW, store=custom, now_ms=now)
    assert result == 2
