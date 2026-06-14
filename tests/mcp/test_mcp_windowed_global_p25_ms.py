"""Item 1011: get_windowed_global_p25_ms() — fleet-wide 25th-percentile latency.

get_windowed_global_p25_ms(window_ms, *, store=None, now_ms=None) -> float

Named convenience alias for get_windowed_global_latency_percentile(25.0, window_ms, ...).
Pools ALL tool latencies before computing percentile. Fleet-wide dual of item-1010.

Discriminating tests:
  1. PRIMARY DISC.: tool_a[50,100] + tool_b[200,400] -> pooled [50,100,200,400] -> 87.5
       idx=0.25*(4-1)=0.75 -> 50+0.75*(100-50)=87.5
       (kills floor=50.0; kills ceil=100.0; correct interpolated=87.5)
  2. POOLED NOT AVG: kills per-tool-avg-of-p25s
  3. Consistent with get_windowed_global_latency_percentile(25.0, ...).
  4. Single tool: global_p25 == per-tool p25_ms.
  5. Empty store -> 0.0.
  6. Old calls excluded.
  7. Returns float.
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_global_p25_ms,
    get_windowed_global_latency_percentile,
    get_windowed_tool_p25_ms,
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


def test_pooled_interpolated_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a[50,100] + tool_b[200,400] -> pooled p25=87.5.

    pooled sorted [50,100,200,400], n=4:
      idx = 0.25 * (4-1) = 0.75
      sorted[0] = 50, sorted[1] = 100
      pooled = 50 + 0.75 * (100 - 50) = 87.5          (CORRECT)

    per-tool:
      tool_a [50, 100]: idx=0.25*1=0.25 -> 50+0.25*50=62.5
      tool_b [200, 400]: idx=0.25 -> 200+0.25*200=250.0
      avg-of-per-tool-p25s = (62.5 + 250.0) / 2 = 156.25  (WRONG)

    Kills floor=50.0, ceil=100.0, and avg-per-tool=156.25.
    """
    store: dict = {}
    ts = _recent()
    for lat in [50.0, 100.0]:
        _add(store, "gp25_a", lat, ts)
    for lat in [200.0, 400.0]:
        _add(store, "gp25_b", lat, ts)

    result = get_windowed_global_p25_ms(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 87.5) < 1e-9, (
        f"pooled p25=87.5; kills floor=50, ceil=100, avg-per-tool=156.25; got {result}"
    )
    assert abs(result - 156.25) > 1.0, "Fixture degenerate: pooled == avg-per-tool"


def test_consistent_with_global_latency_percentile_25() -> None:
    """global_p25_ms == get_windowed_global_latency_percentile(25.0, ...)."""
    store: dict = {}
    ts = _recent()
    for tool, lats in [("gp25_c", [10.0, 30.0, 50.0]), ("gp25_d", [70.0, 90.0])]:
        for lat in lats:
            _add(store, tool, lat, ts)

    direct = get_windowed_global_p25_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    via_pct = get_windowed_global_latency_percentile(25.0, WINDOW_MS, store=store, now_ms=NOW_MS)

    assert abs(direct - via_pct) < 1e-9, (
        f"global_p25_ms={direct} must equal global_latency_percentile(25.0)={via_pct}"
    )


def test_single_tool_matches_per_tool_p25() -> None:
    """With one tool, global p25 == per-tool p25."""
    store: dict = {}
    ts = _recent()
    for lat in [10.0, 20.0, 30.0, 40.0, 50.0]:
        _add(store, "gp25_e", lat, ts)

    global_p25 = get_windowed_global_p25_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    per_tool = get_windowed_tool_p25_ms("gp25_e", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert abs(global_p25 - per_tool) < 1e-9, (
        f"single tool: global_p25={global_p25} must equal per_tool_p25={per_tool}"
    )


def test_empty_store_returns_zero() -> None:
    result = get_windowed_global_p25_ms(WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_old_calls_excluded() -> None:
    """Old calls outside window must not affect fleet p25."""
    store: dict = {}
    for _ in range(5):
        _add(store, "gp25_old", 9999.0, _old())
    for lat in [10.0, 20.0, 30.0, 40.0, 50.0]:
        _add(store, "gp25_old", lat, _recent())

    result = get_windowed_global_p25_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    # [10,20,30,40,50]: idx=0.25*4=1.0 -> 20.0
    assert abs(result - 20.0) < 1e-9, f"Old excluded; p25([10,20,30,40,50])=20.0; got {result}"


def test_returns_float() -> None:
    store: dict = {}
    for lat in [10.0, 20.0, 30.0, 40.0]:
        _add(store, "gp25_rt", lat, _recent())
    result = get_windowed_global_p25_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float), f"Must return float; got {type(result)}"
