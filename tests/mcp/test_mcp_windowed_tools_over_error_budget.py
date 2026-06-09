"""Item 967: get_windowed_tools_over_error_budget() -- SLO violation filter.

get_windowed_tools_over_error_budget(budget_rate, window_ms, *, store=None, now_ms=None)
    -> list[str]

Returns sorted (alphabetical) list of tools with >=1 recent call AND actual_rate > budget_rate.
budget_rate=0 -> all active tools with any error (rate > 0).
Empty when none exceed budget or no recent calls.

Discriminating tests:
  1. PRIMARY DISC.: 3 tools with rates [0.5, 0.1, 0.2], budget_rate=0.15
     -> [tool_0.2, tool_0.5] alphabetically sorted (not [tool_0.5, tool_0.2] by rate)
     (kills impl returning all tools regardless of budget).
  2. budget_rate=0 -> all active tools with any error returned.
  3. No tools over budget -> [].
  4. Old calls excluded.
  5. Returns list[str] sorted alphabetically.
"""
from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_tools_over_error_budget,
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


def test_filters_by_budget_and_returns_alphabetical_primary_discriminator() -> None:
    """PRIMARY DISC.: 3 tools, rates [0.5, 0.1, 0.2], budget=0.15 -> 2 violators sorted."""
    store: dict = {}
    ts = _recent()
    # "beta": 1/2 = 0.5 -> over budget
    _add(store, "beta", 10.0, ts, ok=False)
    _add(store, "beta", 10.0, ts, ok=True)
    # "alpha": 1/5 = 0.2 -> over budget
    for _ in range(4):
        _add(store, "alpha", 10.0, ts, ok=True)
    _add(store, "alpha", 10.0, ts, ok=False)
    # "gamma": 1/10 = 0.1 -> under budget
    for _ in range(9):
        _add(store, "gamma", 10.0, ts, ok=True)
    _add(store, "gamma", 10.0, ts, ok=False)

    result = get_windowed_tools_over_error_budget(
        0.15, WINDOW_MS, store=store, now_ms=NOW_MS
    )

    assert result == ["alpha", "beta"], (
        f"alpha(0.2)>0.15, beta(0.5)>0.15, gamma(0.1)<=0.15; sorted = [alpha, beta]; got {result}"
    )


def test_budget_zero_returns_all_tools_with_any_error() -> None:
    """budget_rate=0 -> any tool with rate > 0 is over budget."""
    store: dict = {}
    ts = _recent()
    _add(store, "err_tool", 10.0, ts, ok=False)  # rate=1.0 > 0
    for _ in range(3):
        _add(store, "clean", 10.0, ts, ok=True)  # rate=0.0, not > 0

    result = get_windowed_tools_over_error_budget(
        0.0, WINDOW_MS, store=store, now_ms=NOW_MS
    )
    assert "err_tool" in result
    assert "clean" not in result


def test_no_violators_returns_empty() -> None:
    """All tools under budget -> []."""
    store: dict = {}
    ts = _recent()
    for _ in range(10):
        _add(store, "t", 10.0, ts, ok=True)
    # 0 errors -> rate=0 < budget=0.1

    result = get_windowed_tools_over_error_budget(
        0.1, WINDOW_MS, store=store, now_ms=NOW_MS
    )
    assert result == []


def test_old_calls_excluded() -> None:
    """Only recent calls determine whether a tool is over budget."""
    store: dict = {}
    # Old failing calls -- if included, rate=1.0 -> over budget
    for _ in range(5):
        _add(store, "t", 10.0, _old(), ok=False)
    # Recent call: 0 errors -> rate=0.0 -> under budget
    _add(store, "t", 10.0, _recent(), ok=True)

    result = get_windowed_tools_over_error_budget(
        0.1, WINDOW_MS, store=store, now_ms=NOW_MS
    )
    assert result == [], f"Old failing calls excluded -> rate=0.0 -> under budget; got {result}"


def test_empty_store_returns_empty() -> None:
    result = get_windowed_tools_over_error_budget(0.1, WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == []


def test_returns_sorted_list() -> None:
    """Result is alphabetically sorted."""
    store: dict = {}
    ts = _recent()
    for name in ["zeta", "alpha", "mu"]:
        _add(store, name, 10.0, ts, ok=False)

    result = get_windowed_tools_over_error_budget(
        0.0, WINDOW_MS, store=store, now_ms=NOW_MS
    )
    assert result == sorted(result), f"Result must be alphabetically sorted; got {result}"
    assert set(result) == {"alpha", "mu", "zeta"}
