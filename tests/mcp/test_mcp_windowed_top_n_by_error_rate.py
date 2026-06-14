"""Item 964: get_windowed_top_n_tools_by_error_rate() -- top-N by windowed error rate.

get_windowed_top_n_tools_by_error_rate(n, window_ms, *, store=None, now_ms=None) -> list[str]

Returns up to n tool names sorted descending by windowed error rate.
Only tools with >=1 call in window are eligible (error rate undefined for 0 calls).
Ties broken alphabetically ascending. Empty list when empty/no recent calls.

Discriminating tests:
  1. PRIMARY DISC.: 3 tools: A=0 errors/3 calls, B=2/2 errors (rate=1.0), C=1/4 (rate=0.25)
     n=2 -> [B, C] (kills impl ranking by error COUNT instead of RATE: C has 1 error,
     B has 2 -- count-based gives [B, C] in this case but B=2/2 != C=1/4 rate-wise).
     True discriminating scenario: B=1/1 (rate=1.0), C=2/10 (rate=0.2), n=1 -> [B] not [C].
  2. Tool with 0 windowed calls excluded.
  3. Old calls excluded.
  4. n=0 -> [].
  5. Ties broken alphabetically.
  6. Returns list[str].
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_top_n_tools_by_error_rate,
)

NOW_MS = 100_000.0
WINDOW_MS = 10_000.0


@pytest.fixture(autouse=True)
def _clean():
    _WINDOWED_TELEMETRY.clear()
    yield
    _WINDOWED_TELEMETRY.clear()


def _add(store: dict, tool: str, lat: float, ts: float, ok: bool = True) -> None:
    store.setdefault(tool, []).append((ts, lat, ok))


def _recent() -> float:
    return NOW_MS - 5_000.0


def _old() -> float:
    return NOW_MS - WINDOW_MS - 1_000.0


def test_ranked_by_rate_not_count_primary_discriminator() -> None:
    """PRIMARY DISC.: rate=1.0 (1 error/1 call) beats rate=0.2 (2 errors/10 calls).

    Kills count-based impl: C has 2 error calls but lower RATE than B's 1 error.
    """
    store: dict = {}
    ts = _recent()
    # B: 1 error / 1 call = rate 1.0
    _add(store, "b", 10.0, ts, ok=False)
    # C: 2 errors / 10 calls = rate 0.2
    for _ in range(8):
        _add(store, "c", 10.0, ts, ok=True)
    _add(store, "c", 10.0, ts, ok=False)
    _add(store, "c", 10.0, ts, ok=False)
    # A: 0 errors / 3 calls = rate 0.0
    for _ in range(3):
        _add(store, "a", 10.0, ts, ok=True)

    result = get_windowed_top_n_tools_by_error_rate(1, WINDOW_MS, store=store, now_ms=NOW_MS)

    assert result == ["b"], f"B has highest error rate (1.0 > 0.2); got {result!r}"


def test_full_ranking_n2() -> None:
    """3 tools with rates [1.0, 0.25, 0.0], n=2 -> top 2 ranked by rate."""
    store: dict = {}
    ts = _recent()
    _add(store, "b", 10.0, ts, ok=False)
    _add(store, "b", 10.0, ts, ok=False)
    # b: 2/2 = 1.0
    _add(store, "c", 10.0, ts, ok=True)
    _add(store, "c", 10.0, ts, ok=True)
    _add(store, "c", 10.0, ts, ok=True)
    _add(store, "c", 10.0, ts, ok=False)
    # c: 1/4 = 0.25
    for _ in range(5):
        _add(store, "a", 10.0, ts, ok=True)
    # a: 0/5 = 0.0

    result = get_windowed_top_n_tools_by_error_rate(2, WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == ["b", "c"], f"Expected [b, c]; got {result}"


def test_zero_windowed_calls_tool_excluded() -> None:
    """Tool with only old calls must not appear."""
    store: dict = {}
    _add(store, "recent", 10.0, _recent(), ok=False)
    _add(store, "ancient", 10.0, _old(), ok=False)  # 100% error rate but outside window

    result = get_windowed_top_n_tools_by_error_rate(5, WINDOW_MS, store=store, now_ms=NOW_MS)
    assert "ancient" not in result, f"ancient must be excluded; got {result}"


def test_n_zero_returns_empty() -> None:
    store: dict = {}
    _add(store, "t", 10.0, _recent(), ok=False)
    result = get_windowed_top_n_tools_by_error_rate(0, WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == []


def test_ties_broken_alphabetically() -> None:
    """Two tools with same windowed error rate -> alphabetically first."""
    store: dict = {}
    ts = _recent()
    _add(store, "zeta", 10.0, ts, ok=False)
    _add(store, "alpha", 10.0, ts, ok=False)

    result = get_windowed_top_n_tools_by_error_rate(2, WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == ["alpha", "zeta"], f"Tied at 1.0; alphabetical order; got {result}"


def test_empty_store_returns_empty() -> None:
    result = get_windowed_top_n_tools_by_error_rate(5, WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == []


def test_returns_list() -> None:
    store: dict = {}
    _add(store, "t", 10.0, _recent(), ok=False)
    result = get_windowed_top_n_tools_by_error_rate(1, WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, list)
