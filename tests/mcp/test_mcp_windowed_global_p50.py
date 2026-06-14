"""Item 956: get_windowed_global_p50_ms() -- pooled p50 across all tools in window.

Discriminating tests:
  1. PRIMARY DISC.: tool A=[10,10,10], tool B=[100] -> pooled p50=10.0
     (kills avg-of-p50s=(10+100)/2=55 WRONG).
  2. Empty -> 0.0.
  3. Old calls excluded.
  4. Returns float.
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_global_p50_ms,
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


def test_pooled_p50_not_avg_of_p50s_primary_discriminator() -> None:
    """PRIMARY DISC.: tool A=[10,10,10], tool B=[100] -> pooled p50=10.0 (not 55)."""
    store: dict = {}
    ts = NOW_MS - 5_000.0
    for _ in range(3):
        _add(store, "a", 10.0, ts)
    _add(store, "b", 100.0, ts)

    result = get_windowed_global_p50_ms(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    # pooled [10,10,10,100] -> sorted, p50 = index 1.5 -> 10+0.5*(10-10)=10.0
    assert abs(result - 10.0) < 1e-9, f"Pooled p50=10.0; avg-of-p50s=55.0; got {result}"


def test_empty_store_returns_zero() -> None:
    result = get_windowed_global_p50_ms(WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_old_calls_excluded() -> None:
    store: dict = {}
    old_ts = NOW_MS - WINDOW_MS - 1_000.0
    _add(store, "t", 999.0, old_ts)
    _add(store, "t", 10.0, NOW_MS - 5_000.0)
    result = get_windowed_global_p50_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 10.0, f"Old call excluded -> p50=10.0; got {result}"


def test_returns_float() -> None:
    store: dict = {}
    _add(store, "t", 20.0, NOW_MS - 5_000.0)
    result = get_windowed_global_p50_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float)
