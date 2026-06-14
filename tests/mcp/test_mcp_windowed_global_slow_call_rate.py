"""Item 1006: get_windowed_global_slow_call_rate() — fleet-wide SLO violation rate.

get_windowed_global_slow_call_rate(window_ms, threshold_ms, *, store=None, now_ms=None) -> float

slow_count_all_tools / total_count_all_tools — pooled fraction exceeding threshold.

Discriminating tests:
  1. PRIMARY DISC.: tool_a[10,200] + tool_b[300,50] threshold=100 -> 0.5 (2/4)
       (kills slow_count=2 int; kills total=4 int)
  2. UNEQUAL DIST. DISC.: tool_a[200,300] (all slow) + tool_b[10,20,30] (none slow)
       -> 2/5 = 0.4 (kills avg-of-per-tool-rates = (1.0+0.0)/2 = 0.5)
  3. STRICT GT DISC.: threshold=100, [100.0, 100.0, 200.0] -> 1/3 ≈ 0.333
       (kills >= which gives 3/3 = 1.0)
  4. Empty store -> 0.0.
  5. Old calls excluded.
  6. Returns float in [0.0, 1.0].
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_global_slow_call_rate,
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


def test_primary_discriminator_rate_not_count() -> None:
    """PRIMARY DISC.: tool_a[10,200] + tool_b[300,50] threshold=100 -> 0.5.

    2 slow [200, 300] / 4 total = 0.5.
    Kills impl returning slow_count=2 (int).
    Kills impl returning total_count=4 (int).
    """
    store: dict = {}
    ts = _recent()
    for lat in [10.0, 200.0]:
        _add(store, "gsr_a", lat, ts)
    for lat in [300.0, 50.0]:
        _add(store, "gsr_b", lat, ts)

    result = get_windowed_global_slow_call_rate(WINDOW_MS, 100.0, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 0.5) < 1e-9, f"2/4=0.5; kills slow_count=2 int or total=4 int; got {result}"
    assert 0.0 <= result <= 1.0


def test_unequal_distribution_kills_avg_of_per_tool_rates() -> None:
    """UNEQUAL DIST. DISC.: tool_a (2 slow/2 total, rate=1.0) + tool_b (0 slow/3 total, rate=0.0).

    avg-of-per-tool-rates = (1.0 + 0.0) / 2 = 0.5   (WRONG)
    pooled rate = 2 slow / 5 total = 0.4             (CORRECT)

    This is the decisive discriminator for global-vs-per-tool-average implementations.
    """
    store: dict = {}
    ts = _recent()
    for lat in [200.0, 300.0]:  # tool_a: 2 slow / 2 total = 1.0
        _add(store, "gsr_ua", lat, ts)
    for lat in [10.0, 20.0, 30.0]:  # tool_b: 0 slow / 3 total = 0.0
        _add(store, "gsr_ub", lat, ts)

    result = get_windowed_global_slow_call_rate(WINDOW_MS, 100.0, store=store, now_ms=NOW_MS)

    assert abs(result - 0.4) < 1e-9, (
        f"pooled=2/5=0.4; kills avg-per-tool=(1.0+0.0)/2=0.5; got {result}"
    )
    # Confirm the wrong answer is distinct (not a degenerate fixture)
    assert abs(result - 0.5) > 0.05, "Fixture is degenerate: pooled == avg-per-tool"


def test_strict_gt_not_gte() -> None:
    """STRICT GT DISC.: lats=[100.0, 100.0, 200.0] threshold=100 -> 1/3 ≈ 0.333.

    100.0 == threshold → NOT slow.
    200.0 > 100.0 → slow.
    Kills >= implementation (would give 3/3 = 1.0).
    """
    store: dict = {}
    ts = _recent()
    for lat in [100.0, 100.0, 200.0]:
        _add(store, "gsr_gt", lat, ts)

    result = get_windowed_global_slow_call_rate(WINDOW_MS, 100.0, store=store, now_ms=NOW_MS)

    expected = 1.0 / 3.0
    assert abs(result - expected) < 1e-9, (
        f"strict >: 1/3={expected:.6f}; kills >=impl=1.0; got {result}"
    )


def test_empty_store_returns_zero_float() -> None:
    result = get_windowed_global_slow_call_rate(WINDOW_MS, 100.0, store={}, now_ms=NOW_MS)
    assert isinstance(result, float)
    assert result == 0.0


def test_old_calls_excluded() -> None:
    """Old calls outside the window do not affect the rate."""
    store: dict = {}
    for _ in range(10):
        _add(store, "gsr_old", 9999.0, _old())
    for lat in [10.0, 20.0, 30.0]:
        _add(store, "gsr_old", lat, _recent())

    result = get_windowed_global_slow_call_rate(WINDOW_MS, 100.0, store=store, now_ms=NOW_MS)

    assert result == 0.0, f"Old excluded; all recent < 100ms -> 0.0; got {result}"


def test_all_slow_returns_one() -> None:
    store: dict = {}
    for tool in ["gsr_s1", "gsr_s2"]:
        for lat in [200.0, 300.0]:
            _add(store, tool, lat, _recent())
    result = get_windowed_global_slow_call_rate(WINDOW_MS, 100.0, store=store, now_ms=NOW_MS)
    assert abs(result - 1.0) < 1e-9, f"All slow -> 1.0; got {result}"
