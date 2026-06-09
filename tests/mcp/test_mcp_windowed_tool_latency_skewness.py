"""Item 1022: get_windowed_tool_latency_skewness() — per-tool latency skewness.

get_windowed_tool_latency_skewness(tool_name, window_ms, *, store=None, now_ms=None) -> float

Population skewness = mean(((lat - mean) / stddev) ** 3)
0.0 for < 3 calls, stddev == 0, or no recent calls.

Positive skew = right tail (occasional slow outliers).
Negative skew = left tail (occasional fast outliers, rare).

Discriminating tests:
  1. PRIMARY DISC.: lats [10, 10, 10, 100] -> skewness ≈ 1.1547
       NOTE: backlog spec stated 0.897 — WRONG; correct population skewness ≈ 1.1547
       (kills stddev=38.97 float; kills mean=32.5 float; kills variance=1518.75 float)
  2. All-equal latencies -> 0.0 (stddev=0 guard)
  3. Fewer-than-3 calls -> 0.0
  4. Old calls excluded
  5. Symmetric distribution -> 0.0 (no skew)
  6. Returns float
"""
from __future__ import annotations

import math

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_tool_latency_skewness,
)

NOW_MS = 100_000.0
WINDOW_MS = 10_000.0
CUTOFF_MS = NOW_MS - WINDOW_MS


@pytest.fixture(autouse=True)
def _clean():
    _WINDOWED_TELEMETRY.clear()
    yield
    _WINDOWED_TELEMETRY.clear()


def _add(store: dict, tool: str, lat: float, ts: float, ok: bool = True) -> None:
    store.setdefault(tool, []).append((ts, lat, ok))


def _recent(offset: float = 0.0) -> float:
    return NOW_MS - 500.0 + offset


def _old() -> float:
    return NOW_MS - WINDOW_MS - 1_000.0


def test_right_skew_not_stddev_not_mean_primary_discriminator() -> None:
    """PRIMARY DISC.: lats [10, 10, 10, 100] -> skewness ≈ 1.1547.

    Kills impl returning mean=32.5 (different value).
    Kills impl returning stddev=38.97 (different value).
    Kills impl returning variance=1518.75 (different value).
    Backlog spec stated 0.897 — that value is WRONG; 1.1547 is correct.
    """
    store: dict = {}
    for i, lat in enumerate([10.0, 10.0, 10.0, 100.0]):
        _add(store, "sk_t", lat, _recent(float(i)))

    result = get_windowed_tool_latency_skewness("sk_t", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    # population skewness = mean(z^3) where z = (x - mu)/sigma
    # mu=32.5, sigma=38.971, skew ≈ 1.1547
    assert abs(result - 1.154701) < 1e-4, (
        f"skewness≈1.1547; kills stddev=38.97 or mean=32.5; got {result}"
    )


def test_all_equal_returns_zero() -> None:
    """All latencies equal -> stddev=0 -> skewness=0.0 (not ZeroDivisionError, not NaN)."""
    store: dict = {}
    for i in range(4):
        _add(store, "sk_eq", 50.0, _recent(float(i)))

    result = get_windowed_tool_latency_skewness("sk_eq", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert result == 0.0, f"All equal -> 0.0; got {result}"
    assert math.isfinite(result), "Must not be NaN or inf"


def test_fewer_than_three_calls_returns_zero() -> None:
    """<3 calls -> 0.0 (skewness undefined for 1 or 2 data points)."""
    store: dict = {}
    _add(store, "sk_two", 10.0, _recent(0.0))
    _add(store, "sk_two", 100.0, _recent(1.0))

    result = get_windowed_tool_latency_skewness("sk_two", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert result == 0.0, f"2 calls -> 0.0; got {result}"


def test_single_call_returns_zero() -> None:
    """1 call -> 0.0."""
    store: dict = {}
    _add(store, "sk_one", 42.0, _recent(0.0))

    result = get_windowed_tool_latency_skewness("sk_one", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert result == 0.0, f"Single call -> 0.0; got {result}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    result = get_windowed_tool_latency_skewness("no_such", WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_old_calls_excluded() -> None:
    """Old calls must not affect skewness calculation."""
    store: dict = {}
    # Old calls with extreme latency — would create massive skew
    for _ in range(5):
        _add(store, "sk_old", 99999.0, _old())
    # Recent calls: symmetric [10, 20, 30] -> near-zero skew
    for i, lat in enumerate([10.0, 20.0, 30.0]):
        _add(store, "sk_old", lat, _recent(float(i)))

    result = get_windowed_tool_latency_skewness("sk_old", WINDOW_MS, store=store, now_ms=NOW_MS)

    # Symmetric distribution [10, 20, 30]: skewness should be 0.0
    assert abs(result) < 1e-9, (
        f"Old excluded; symmetric [10,20,30] -> 0.0; got {result}"
    )


def test_symmetric_distribution_returns_zero() -> None:
    """Perfectly symmetric distribution -> skewness = 0.0."""
    store: dict = {}
    # [10, 20, 30] is arithmetic sequence — perfectly symmetric
    for i, lat in enumerate([10.0, 20.0, 30.0]):
        _add(store, "sk_sym", lat, _recent(float(i)))

    result = get_windowed_tool_latency_skewness("sk_sym", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert abs(result) < 1e-9, f"Symmetric [10,20,30] -> 0.0; got {result}"


def test_returns_float() -> None:
    """Return type must be float."""
    store: dict = {}
    for i, lat in enumerate([10.0, 50.0, 100.0, 200.0]):
        _add(store, "sk_rt", lat, _recent(float(i)))

    result = get_windowed_tool_latency_skewness("sk_rt", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float), f"Must return float; got {type(result)}"
