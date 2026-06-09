"""Item 1004: get_windowed_tool_slow_call_rate() — SLO violation rate.

get_windowed_tool_slow_call_rate(tool_name, window_ms, threshold_ms, *, store=None, now_ms=None) -> float

slow_call_count / total_call_count — fraction of calls exceeding the threshold.

Discriminating tests:
  1. PRIMARY DISC.: lats [10, 50, 200, 300] with threshold=100 -> 0.5
       (kills slow_count=2 int; kills total=4 int; correct=2/4=0.5 float in [0,1])
  2. STRICT GT DISC.: threshold=50, lats [10, 50, 200] -> 1/3 ≈ 0.333
       (kills >= which gives 2/3 ≈ 0.667)
  3. All fast -> 0.0 (not 0 int).
  4. All slow -> 1.0 (not count).
  5. Unknown tool -> 0.0.
  6. Old calls excluded.
  7. Returns float in [0.0, 1.0].
"""
from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_tool_slow_call_rate,
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


def test_rate_not_count_not_total_primary_discriminator() -> None:
    """PRIMARY DISC.: lats [10, 50, 200, 300] threshold=100 -> 0.5 (2/4).

    slow count = 2     (int — WRONG unit)
    total count = 4    (int — WRONG unit)
    rate = 2/4 = 0.5   (float in [0,1] — CORRECT)

    Kills impl returning raw count.
    Kills impl returning total.
    """
    store: dict = {}
    ts = _recent()
    for lat in [10.0, 50.0, 200.0, 300.0]:
        _add(store, "t", lat, ts)

    result = get_windowed_tool_slow_call_rate("t", WINDOW_MS, 100.0, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 0.5) < 1e-9, (
        f"2/4=0.5; kills slow_count=2 or total=4; got {result}"
    )
    assert 0.0 <= result <= 1.0, f"Rate must be in [0,1]; got {result}"


def test_strictly_greater_than_not_gte() -> None:
    """STRICT GT DISC.: threshold=50, lats [10, 50, 200] -> 1/3 ≈ 0.333.

    50 == threshold → NOT slow (strictly >)
    Kills >= implementation (would give 2/3 ≈ 0.667).
    """
    store: dict = {}
    ts = _recent()
    for lat in [10.0, 50.0, 200.0]:
        _add(store, "t_gt", lat, ts)

    result = get_windowed_tool_slow_call_rate("t_gt", WINDOW_MS, 50.0, store=store, now_ms=NOW_MS)

    expected = 1.0 / 3.0
    assert abs(result - expected) < 1e-9, (
        f"strict >: 1/3={expected:.6f}; kills >=impl=2/3; got {result}"
    )


def test_all_fast_returns_zero() -> None:
    """All calls below threshold -> rate=0.0 (not 0 int)."""
    store: dict = {}
    for lat in [5.0, 10.0, 20.0]:
        _add(store, "t_fast", lat, _recent())
    result = get_windowed_tool_slow_call_rate(
        "t_fast", WINDOW_MS, 100.0, store=store, now_ms=NOW_MS
    )
    assert isinstance(result, float)
    assert result == 0.0, f"All fast -> 0.0; got {result}"


def test_all_slow_returns_one() -> None:
    """All calls above threshold -> rate=1.0."""
    store: dict = {}
    for lat in [200.0, 300.0, 500.0]:
        _add(store, "t_slow", lat, _recent())
    result = get_windowed_tool_slow_call_rate(
        "t_slow", WINDOW_MS, 100.0, store=store, now_ms=NOW_MS
    )
    assert abs(result - 1.0) < 1e-9, f"All slow -> 1.0; got {result}"


def test_unknown_tool_returns_zero() -> None:
    result = get_windowed_tool_slow_call_rate("no_such", WINDOW_MS, 100.0, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_old_calls_excluded() -> None:
    store: dict = {}
    for _ in range(10):
        _add(store, "t_old", 9999.0, _old())
    for lat in [10.0, 20.0, 30.0]:  # all fast, all recent
        _add(store, "t_old", lat, _recent())
    result = get_windowed_tool_slow_call_rate(
        "t_old", WINDOW_MS, 100.0, store=store, now_ms=NOW_MS
    )
    assert result == 0.0, f"Old excluded; all recent < 100ms -> rate=0.0; got {result}"


def test_returns_float() -> None:
    store: dict = {}
    for lat in [50.0, 200.0]:
        _add(store, "t_f", lat, _recent())
    result = get_windowed_tool_slow_call_rate(
        "t_f", WINDOW_MS, 100.0, store=store, now_ms=NOW_MS
    )
    assert isinstance(result, float), f"Must return float; got {type(result)}"
