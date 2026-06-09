"""Item 991: get_windowed_tool_p95_ms() -- per-tool p95 latency shortcut.

get_windowed_tool_p95_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float

Convenience shortcut for get_windowed_latency_percentile(tool, 95, ...).
Per-tool dual of get_windowed_global_p95_ms (item 922).
0.0 for unknown tool or no recent calls.

Discriminating tests:
  1. PRIMARY DISC.: lats [10, 20, 30, 40, 50] -> p95=48.0
     (kills p50=30.0; kills max=50.0; idx=0.95*4=3.8 -> 40+0.8*10=48.0).
  2. Consistent with get_windowed_latency_percentile(tool, 95, ...).
  3. Unknown tool -> 0.0.
  4. Old calls excluded.
  5. Returns float.
  6. Large outlier included: [10, 20, 30, 40, 1000] -> p95=760.0 (not 1000.0).
"""
from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_latency_percentile,
    get_windowed_tool_p95_ms,
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


def test_p95_interpolation_not_max_not_p50_primary_discriminator() -> None:
    """PRIMARY DISC.: lats [10,20,30,40,50] -> p95=48.0 (not max=50, not p50=30).

    idx = 0.95 * (5-1) = 3.8
    lo=3 (40.0), hi=4 (50.0)
    p95 = 40.0 + 0.8 * (50.0 - 40.0) = 48.0

    Kills impl returning max=50.0 (off by one tail).
    Kills impl returning p50=30.0 (wrong percentile).
    """
    store: dict = {}
    ts = _recent()
    for lat in [50.0, 10.0, 30.0, 20.0, 40.0]:  # unsorted insertion
        _add(store, "t", lat, ts)

    result = get_windowed_tool_p95_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 48.0) < 1e-9, (
        f"p95([10,20,30,40,50]): idx=3.8 -> 48.0; kills max=50.0 or p50=30.0; got {result}"
    )


def test_consistent_with_latency_percentile() -> None:
    """Must equal get_windowed_latency_percentile(tool, 95.0, ...)."""
    store: dict = {}
    ts = _recent()
    for lat in [5.0, 15.0, 25.0, 35.0, 45.0, 80.0, 100.0, 200.0]:
        _add(store, "t", lat, ts)

    shortcut = get_windowed_tool_p95_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    full = get_windowed_latency_percentile("t", 95.0, WINDOW_MS, store=store, now_ms=NOW_MS)

    assert abs(shortcut - full) < 1e-9, (
        f"shortcut={shortcut} must equal latency_percentile(95)={full}"
    )


def test_unknown_tool_returns_zero() -> None:
    result = get_windowed_tool_p95_ms("no_such_tool", WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_old_calls_excluded() -> None:
    """Huge old latencies must not pollute p95."""
    store: dict = {}
    for _ in range(10):
        _add(store, "t", 9999.0, _old())   # huge outside window
    for lat in [10.0, 20.0, 30.0, 40.0, 50.0]:
        _add(store, "t", lat, _recent())

    result = get_windowed_tool_p95_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 48.0) < 1e-9, (
        f"Old excluded; p95([10,20,30,40,50])=48.0; got {result}"
    )


def test_large_outlier_not_returned_as_p95() -> None:
    """Outlier tail: [10, 20, 30, 40, 1000] -> p95 is interpolated, NOT 1000.

    idx = 0.95 * 4 = 3.8 -> 40 + 0.8*(1000-40) = 40 + 768 = 808.0.
    (Not max=1000.0; the 95th percentile does not equal the maximum.)
    """
    store: dict = {}
    ts = _recent()
    for lat in [10.0, 20.0, 30.0, 40.0, 1000.0]:
        _add(store, "t", lat, ts)

    result = get_windowed_tool_p95_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 808.0) < 1e-9, (
        f"p95([10,20,30,40,1000]): 40+0.8*960=808.0; got {result}"
    )
    assert result < 1000.0, "p95 must be LESS than max for non-trivial distributions"


def test_returns_float() -> None:
    store: dict = {}
    _add(store, "t", 42.0, _recent())
    result = get_windowed_tool_p95_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float), f"Must return float; got {type(result)}"
