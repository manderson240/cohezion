"""Item 955: get_windowed_global_mean_latency_ms() -- mean latency in window.

get_windowed_global_mean_latency_ms(window_ms, *, store=None, now_ms=None) -> float

Pooled mean: total_windowed_latency / total_windowed_calls across all tools.
0.0 when no recent calls.

Discriminating tests:
  1. PRIMARY DISC.: tool A=[10,10,10], tool B=[100] -> correct 130/4=32.5;
     avg-of-means (10+100)/2=55 WRONG.
  2. Empty store -> 0.0.
  3. Old calls excluded.
  4. Returns float.
"""
from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_global_mean_latency_ms,
)

NOW_MS = 100_000.0
WINDOW_MS = 10_000.0


@pytest.fixture(autouse=True)
def _clean():
    _WINDOWED_TELEMETRY.clear()
    yield
    _WINDOWED_TELEMETRY.clear()


def _add(store: dict, tool: str, lat: float, ts: float) -> None:
    store.setdefault(tool, []).append((ts, lat, True))


def _recent() -> float:
    return NOW_MS - 5_000.0


def _old() -> float:
    return NOW_MS - WINDOW_MS - 1_000.0


def test_pooled_mean_not_avg_of_means_primary_discriminator() -> None:
    """PRIMARY DISC.: tool A=[10,10,10], tool B=[100] -> 130/4=32.5, not (10+100)/2=55."""
    store: dict = {}
    ts = _recent()
    for _ in range(3):
        _add(store, "a", 10.0, ts)
    _add(store, "b", 100.0, ts)

    result = get_windowed_global_mean_latency_ms(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float), f"Must be float; got {type(result)}"
    assert abs(result - 32.5) < 1e-9, (
        f"Pooled mean=32.5; avg-of-means=55; got {result}"
    )


def test_empty_store_returns_zero() -> None:
    result = get_windowed_global_mean_latency_ms(WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0, f"Empty -> 0.0; got {result}"


def test_old_calls_excluded() -> None:
    store: dict = {}
    _add(store, "t", 999.0, _old())  # huge old latency
    _add(store, "t", 10.0, _recent())
    result = get_windowed_global_mean_latency_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 10.0, f"Old call excluded -> mean=10.0; got {result}"


def test_returns_float() -> None:
    store: dict = {}
    _add(store, "t", 20.0, _recent())
    result = get_windowed_global_mean_latency_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float), f"Must be float; got {type(result)}"


def test_uses_windowed_telemetry_singleton() -> None:
    _WINDOWED_TELEMETRY["x"] = [(NOW_MS - 5_000.0, 50.0, True)] * 2
    result = get_windowed_global_mean_latency_ms(WINDOW_MS, now_ms=NOW_MS)
    assert result == 50.0, f"Mean of [50,50]=50; got {result}"
