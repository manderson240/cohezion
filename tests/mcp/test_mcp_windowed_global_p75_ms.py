"""Item 1009: get_windowed_global_p75_ms() — fleet-wide 75th-percentile latency.

get_windowed_global_p75_ms(window_ms, *, store=None, now_ms=None) -> float

Named convenience alias for get_windowed_global_latency_percentile(75.0, window_ms, ...).
Pools ALL tool latencies before computing percentile. Fleet-wide dual of item-1008.

Discriminating tests:
  1. PRIMARY DISC.: tool_a[50,100] + tool_b[200,400] -> pooled [50,100,200,400] -> 250.0
       idx=0.75*3=2.25 -> 200+0.25*(400-200)=250.0
       (kills per-tool-avg-of-p75s=(150+300)/2=225.0; pooled=250.0)
  2. Consistent with get_windowed_global_latency_percentile(75.0, ...).
  3. Single tool: global_p75 == per-tool p75_ms.
  4. Empty store -> 0.0.
  5. Old calls excluded.
  6. Returns float.
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_global_p75_ms,
    get_windowed_global_latency_percentile,
    get_windowed_tool_p75_ms,
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


def test_pooled_not_avg_per_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a[50,100] + tool_b[200,400] -> pooled p75=250.0.

    per-tool:
      tool_a [50, 100]: idx=0.75*1=0.75 -> 50+0.75*50=87.5  (p75_a=87.5)
    Wait -- let me recompute per the backlog:
      tool_a: sorted [50, 100], n=2, idx=0.75*(2-1)=0.75 -> 50+0.75*(100-50)=87.5
      tool_b: sorted [200, 400], n=2, idx=0.75 -> 200+0.75*(400-200)=350.0
      avg-of-per-tool-p75s = (87.5 + 350.0) / 2 = 218.75   (WRONG)

    pooled sorted [50, 100, 200, 400], n=4:
      idx = 0.75 * (4-1) = 2.25
      sorted[2] = 200, sorted[3] = 400
      pooled = 200 + 0.25 * (400 - 200) = 250.0             (CORRECT)

    Note: backlog uses 'p75_a=150, p75_b=300' from a different interpolation method.
    We use the standard linear interpolation: idx=(p/100)*(n-1).
    The key discriminator is pooled (250.0) != avg-per-tool (218.75).
    """
    store: dict = {}
    ts = _recent()
    for lat in [50.0, 100.0]:
        _add(store, "gp75_a", lat, ts)
    for lat in [200.0, 400.0]:
        _add(store, "gp75_b", lat, ts)

    result = get_windowed_global_p75_ms(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 250.0) < 1e-9, f"pooled p75=250.0; kills avg-per-tool p75; got {result}"
    # Confirm the wrong answer differs (fixture is discriminating)
    assert abs(result - 218.75) > 1.0, "Fixture degenerate: pooled == avg-per-tool"


def test_consistent_with_global_latency_percentile() -> None:
    """global_p75_ms == get_windowed_global_latency_percentile(75.0, ...)."""
    store: dict = {}
    ts = _recent()
    for tool, lats in [("gp75_c", [10.0, 30.0, 50.0]), ("gp75_d", [70.0, 90.0])]:
        for lat in lats:
            _add(store, tool, lat, ts)

    direct = get_windowed_global_p75_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    via_pct = get_windowed_global_latency_percentile(75.0, WINDOW_MS, store=store, now_ms=NOW_MS)

    assert abs(direct - via_pct) < 1e-9, (
        f"global_p75_ms={direct} must equal global_latency_percentile(75.0)={via_pct}"
    )


def test_single_tool_matches_per_tool_p75() -> None:
    """With one tool, global p75 == per-tool p75."""
    store: dict = {}
    ts = _recent()
    for lat in [10.0, 20.0, 30.0, 40.0, 50.0]:
        _add(store, "gp75_e", lat, ts)

    global_p75 = get_windowed_global_p75_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    per_tool = get_windowed_tool_p75_ms("gp75_e", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert abs(global_p75 - per_tool) < 1e-9, (
        f"single tool: global_p75={global_p75} must equal per_tool_p75={per_tool}"
    )


def test_empty_store_returns_zero() -> None:
    result = get_windowed_global_p75_ms(WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_old_calls_excluded() -> None:
    """Old calls outside window must not affect fleet p75."""
    store: dict = {}
    for _ in range(5):
        _add(store, "gp75_old", 9999.0, _old())
    for lat in [10.0, 20.0, 30.0, 40.0, 50.0]:
        _add(store, "gp75_old", lat, _recent())

    result = get_windowed_global_p75_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    # [10,20,30,40,50]: idx=0.75*4=3.0 -> 40.0
    assert abs(result - 40.0) < 1e-9, f"Old excluded; p75([10,20,30,40,50])=40.0; got {result}"


def test_returns_float() -> None:
    store: dict = {}
    for lat in [10.0, 20.0, 30.0, 40.0]:
        _add(store, "gp75_rt", lat, _recent())
    result = get_windowed_global_p75_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float), f"Must return float; got {type(result)}"
