"""Item 999: get_windowed_tool_latency_iqr_ms() — per-tool IQR latency spread.

get_windowed_tool_latency_iqr_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float

IQR = p75 - p25  (robust spread metric, outlier-resistant).

Discriminating tests:
  1. PRIMARY DISC.: lats [10, 20, 30, 40, 50] -> IQR=20.0
       p75: idx=0.75*4=3.0 -> 40.0
       p25: idx=0.25*4=1.0 -> 20.0
       IQR = 40.0 - 20.0 = 20.0
       (kills range=40.0 == max-min=50-10; kills stddev≈14.1)
  2. OUTLIER DISC.: [10, 20, 30, 40, 9999] -> IQR=20.0 (robust, range=9989 is NOT)
  3. Unknown tool -> 0.0.
  4. Empty store -> 0.0.
  5. Old calls excluded.
  6. Constant latency -> IQR=0.0 (not negative, not error).
  7. Returns float.
"""
from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_tool_latency_iqr_ms,
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


def test_iqr_not_range_not_stddev_primary_discriminator() -> None:
    """PRIMARY DISC.: IQR=20.0 != range=40.0 != stddev≈14.1.

    lats [10, 20, 30, 40, 50]:
      p75: idx=0.75*(5-1)=3.0 -> sorted[3]=40.0  (exact, frac=0)
      p25: idx=0.25*(5-1)=1.0 -> sorted[1]=20.0  (exact, frac=0)
      IQR = 40.0 - 20.0 = 20.0

      range = 50 - 10 = 40.0     (WRONG -- uses min/max not quartiles)
      stddev ≈ 14.14...           (WRONG -- wrong formula entirely)

    Kills impl using max-min as spread.
    Kills impl returning stddev.
    """
    store: dict = {}
    ts = _recent()
    for lat in [50.0, 30.0, 10.0, 40.0, 20.0]:  # unsorted insertion
        _add(store, "t", lat, ts)

    result = get_windowed_tool_latency_iqr_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 20.0) < 1e-9, (
        f"IQR([10,20,30,40,50])=20.0; kills range=40.0 or stddev≈14.1; got {result}"
    )
    # not range (max-min)
    assert abs(result - 40.0) > 1.0, "Should not return range"


def test_iqr_robust_to_outlier() -> None:
    """OUTLIER DISC.: [10, 20, 30, 40, 9999] -> IQR=20.0 (range=9989 is NOT robust).

    p75 and p25 are unaffected by the outlier 9999 — the quartiles still
    lie in the middle of the distribution.  This is the POINT of IQR over range.
    """
    store: dict = {}
    ts = _recent()
    for lat in [10.0, 20.0, 30.0, 40.0, 9999.0]:
        _add(store, "t_out", lat, ts)

    result = get_windowed_tool_latency_iqr_ms("t_out", WINDOW_MS, store=store, now_ms=NOW_MS)

    # IQR: p75=40.0, p25=20.0 -> 20.0 (same as clean distribution)
    assert abs(result - 20.0) < 1e-9, (
        f"Outlier-robust IQR=20.0 (range would be 9989); got {result}"
    )


def test_unknown_tool_returns_zero() -> None:
    result = get_windowed_tool_latency_iqr_ms("no_such", WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_empty_store_returns_zero() -> None:
    result = get_windowed_tool_latency_iqr_ms("t", WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_old_calls_excluded() -> None:
    """Old high-IQR latencies must not pollute the result."""
    store: dict = {}
    for lat in [0.0, 9999.0] * 5:
        _add(store, "t_old", lat, _old())
    # 5 recent calls with IQR=20.0
    for lat in [10.0, 20.0, 30.0, 40.0, 50.0]:
        _add(store, "t_old", lat, _recent())

    result = get_windowed_tool_latency_iqr_ms("t_old", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 20.0) < 1e-9, (
        f"Old excluded; IQR([10,20,30,40,50])=20.0; got {result}"
    )


def test_constant_latency_returns_zero() -> None:
    """All calls same latency -> IQR=0.0 (not negative, not error)."""
    store: dict = {}
    ts = _recent()
    for _ in range(5):
        _add(store, "t_const", 42.0, ts)

    result = get_windowed_tool_latency_iqr_ms("t_const", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 0.0, f"Constant latency -> IQR=0.0; got {result}"


def test_returns_float() -> None:
    store: dict = {}
    for lat in [10.0, 20.0, 30.0]:
        _add(store, "t_f", lat, _recent())
    result = get_windowed_tool_latency_iqr_ms("t_f", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float), f"Must return float; got {type(result)}"
