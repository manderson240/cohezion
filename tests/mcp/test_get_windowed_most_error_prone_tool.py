"""Item 960: get_windowed_most_error_prone_tool(window_ms, *, store=None, now_ms=None) -> str | None
-- tool with the highest windowed error rate.

PRIMARY DISC.: 3 tools A=0/3 errors, B=2/2 errors (rate=1.0), C=1/4 errors (rate=0.25).
B wins with rate=1.0.
Kills impl comparing error counts instead of error rates.
Kills impl returning alphabetically first tool regardless of error rate.
Ties broken alphabetically. None when empty. Returns str | None.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_most_error_prone_tool,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_highest_windowed_error_rate_wins_primary_discriminator() -> None:
    """FALSIFIABLE: A=0/3 errors, B=2/2 errors (rate=1.0), C=1/4 (rate=0.25).
    B has rate=1.0 -> B wins.
    Kills impl comparing error counts (C has 1 error > B's 2 is wrong: rates matter).
    Actually B has 2 errors vs C's 1 error AND B also has rate=1.0 vs 0.25.
    Using counts instead of rates: B(2) > C(1) > A(0) -> same winner accidentally.
    So use distinct count/rate winner: tool with MORE errors but LOWER rate must lose."""
    _reset()
    store = _make_store({
        "wmep_a": [(_NOW - 10, 5.0, True)] * 3,            # 0/3 errors, rate=0.0
        "wmep_b": [(_NOW - 10, 5.0, False)] * 2,           # 2/2 errors, rate=1.0
        "wmep_c": [
            *[(_NOW - 10, 5.0, False)],                     # 1 error
            *[(_NOW - 10, 5.0, True)] * 3,                  # 3 success
        ],  # 1/4 errors, rate=0.25
    })
    result = get_windowed_most_error_prone_tool(_WIN, store=store, now_ms=_NOW)
    assert result == "wmep_b"   # rate=1.0 wins
    assert result != "wmep_a"   # alphabetically first but rate=0.0


def test_count_vs_rate_discriminator() -> None:
    """Kills impl using error count instead of error rate.
    Tool A: 10 errors out of 1000 calls (rate=0.01).
    Tool B: 1 error out of 2 calls (rate=0.5).
    By count: A wins (10 > 1). By rate: B wins (0.5 > 0.01)."""
    _reset()
    store = _make_store({
        "cvr_a": [
            *[(_NOW - 10, 5.0, False)] * 10,    # 10 errors
            *[(_NOW - 10, 5.0, True)] * 990,    # 990 success
        ],
        "cvr_b": [
            (_NOW - 10, 5.0, False),             # 1 error
            (_NOW - 10, 5.0, True),              # 1 success
        ],
    })
    result = get_windowed_most_error_prone_tool(_WIN, store=store, now_ms=_NOW)
    assert result == "cvr_b"   # rate=0.5 wins over rate=0.01


def test_empty_store_returns_none() -> None:
    """No tools -> None."""
    _reset()
    assert get_windowed_most_error_prone_tool(_WIN, store={}, now_ms=_NOW) is None


def test_no_recent_calls_returns_none() -> None:
    """All calls outside window -> None."""
    store = _make_store({
        "wmep_old": [(_NOW - _WIN - 100, 5.0, False)],
    })
    assert get_windowed_most_error_prone_tool(_WIN, store=store, now_ms=_NOW) is None


def test_all_successful_tools_returns_first_alphabetically() -> None:
    """All tools with 0 error rate -> tied at 0.0 -> alphabetically first."""
    store = _make_store({
        "zzz": [(_NOW - 10, 5.0, True)],
        "aaa": [(_NOW - 10, 5.0, True)],
    })
    result = get_windowed_most_error_prone_tool(_WIN, store=store, now_ms=_NOW)
    assert result == "aaa"


def test_tie_broken_alphabetically() -> None:
    """Two tools tied at the same error rate -> alphabetically first."""
    store = _make_store({
        "zzz_err": [(_NOW - 10, 5.0, False)],  # rate = 1.0
        "aaa_err": [(_NOW - 10, 5.0, False)],  # rate = 1.0
    })
    result = get_windowed_most_error_prone_tool(_WIN, store=store, now_ms=_NOW)
    assert result == "aaa_err"
