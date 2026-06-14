"""Item 966: get_windowed_error_budget_used() -- fraction of SLO error budget consumed.

get_windowed_error_budget_used(tool_name, budget_rate, window_ms, *, store=None, now_ms=None)
    -> float

Returns actual_error_rate / budget_rate.
0.0 when no recent calls or budget_rate == 0.
>1.0 allowed (over-budget is meaningful, must NOT be clamped).

Discriminating tests:
  1. PRIMARY DISC.: 2/10 errors (rate=0.2), budget_rate=0.05 -> 4.0
     (kills impl returning rate=0.2 instead of ratio; kills impl clamping at 1.0).
  2. 0 recent calls -> 0.0.
  3. budget_rate=0 -> 0.0 (no div-by-zero).
  4. Under-budget (rate < budget_rate) -> ratio < 1.0.
  5. Exactly at budget -> 1.0.
  6. Returns float.
  7. Old calls excluded (windowed).
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_error_budget_used,
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


def test_over_budget_ratio_not_clamped_primary_discriminator() -> None:
    """PRIMARY DISC.: rate=0.2, budget=0.05 -> ratio=4.0 (not 1.0, not 0.2)."""
    store: dict = {}
    ts = _recent()
    for _ in range(8):
        _add(store, "t", 10.0, ts, ok=True)
    for _ in range(2):
        _add(store, "t", 10.0, ts, ok=False)
    # 2/10 = 0.2 actual; budget=0.05; ratio = 0.2/0.05 = 4.0

    result = get_windowed_error_budget_used("t", 0.05, WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 4.0) < 1e-9, (
        f"rate=0.2, budget=0.05 -> ratio=4.0; kills clamping at 1.0; got {result}"
    )


def test_no_recent_calls_returns_zero() -> None:
    result = get_windowed_error_budget_used("unknown", 0.05, WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_budget_rate_zero_returns_zero() -> None:
    """budget_rate=0 must return 0.0 (no div-by-zero)."""
    store: dict = {}
    _add(store, "t", 10.0, _recent(), ok=False)
    result = get_windowed_error_budget_used("t", 0.0, WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 0.0


def test_under_budget_ratio_less_than_one() -> None:
    """rate=0.05, budget=0.10 -> ratio=0.5 (50% of budget used)."""
    store: dict = {}
    ts = _recent()
    for _ in range(19):
        _add(store, "t", 10.0, ts, ok=True)
    _add(store, "t", 10.0, ts, ok=False)
    # 1/20 = 0.05 actual; budget=0.10; ratio=0.5

    result = get_windowed_error_budget_used("t", 0.10, WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 0.5) < 1e-9, f"0.05/0.10=0.5; got {result}"


def test_exactly_at_budget_returns_one() -> None:
    """rate == budget_rate -> ratio=1.0 (100% budget consumed)."""
    store: dict = {}
    ts = _recent()
    for _ in range(9):
        _add(store, "t", 10.0, ts, ok=True)
    _add(store, "t", 10.0, ts, ok=False)
    # 1/10=0.1; budget=0.1 -> ratio=1.0

    result = get_windowed_error_budget_used("t", 0.1, WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 1.0) < 1e-9, f"rate==budget -> 1.0; got {result}"


def test_old_calls_excluded() -> None:
    """Only recent calls count for budget calculation."""
    store: dict = {}
    # Only old failing call -- if included, error_rate=1.0 -> ratio=20.0
    _add(store, "t", 10.0, _old(), ok=False)
    # One recent successful call -> rate=0.0
    _add(store, "t", 10.0, _recent(), ok=True)

    result = get_windowed_error_budget_used("t", 0.05, WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 0.0, f"Old failing call excluded -> rate=0.0 -> ratio=0.0; got {result}"


def test_returns_float() -> None:
    store: dict = {}
    _add(store, "t", 10.0, _recent(), ok=False)
    result = get_windowed_error_budget_used("t", 0.5, WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float)
