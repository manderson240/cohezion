"""Item 1000: get_windowed_global_latency_iqr_ms() — fleet-wide pooled IQR latency.

get_windowed_global_latency_iqr_ms(window_ms, *, store=None, now_ms=None) -> float

IQR = p75 - p25 of the POOLED latency distribution across ALL tools.
Fleet-wide dual of get_windowed_tool_latency_iqr_ms (item 999).

Discriminating tests:
  1. PRIMARY DISC.: tool_a [10,50] + tool_b [20,30]
       -> pooled sorted [10,20,30,50]
       p75: idx=0.75*3=2.25 -> 30+0.25*(50-30)=35.0
       p25: idx=0.25*3=0.75 -> 10+0.75*(20-10)=17.5
       IQR = 35.0 - 17.5 = 17.5
       avg-of-per-tool-IQR = (20.0+5.0)/2 = 12.5  (WRONG -- linear interp avg)
       global range = 50-10 = 40.0                 (WRONG -- uses min/max)
  2. Consistent with get_windowed_global_latency_percentile(75,...) - (25,...).
  3. Single tool matches per-tool IQR.
  4. Empty store -> 0.0.
  5. Old calls excluded.
  6. Returns float.
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_global_latency_iqr_ms,
    get_windowed_global_latency_percentile,
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


def test_pooled_iqr_not_avg_per_tool_not_global_range_primary_discriminator() -> None:
    """PRIMARY DISC.: pooled IQR=17.5 != avg-per-tool=12.5 != global range=40.0.

    tool_a [10, 50]:
      p75=40.0, p25=20.0, IQR_a=20.0
    tool_b [20, 30]:
      p75=27.5, p25=22.5, IQR_b=5.0
    avg-of-per-tool-IQR = (20.0 + 5.0) / 2 = 12.5  (WRONG)
    global range = 50-10 = 40.0                      (WRONG)

    pooled [10,20,30,50]:
      p75: idx=0.75*3=2.25 -> 30+0.25*20=35.0
      p25: idx=0.25*3=0.75 -> 10+0.75*10=17.5
      IQR = 35.0 - 17.5 = 17.5                      (CORRECT)
    """
    store: dict = {}
    ts = _recent()
    _add(store, "gi_a", 10.0, ts)
    _add(store, "gi_a", 50.0, ts)
    _add(store, "gi_b", 20.0, ts)
    _add(store, "gi_b", 30.0, ts)

    result = get_windowed_global_latency_iqr_ms(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 17.5) < 1e-9, (
        f"pooled IQR=17.5; kills avg-per-tool=12.5 or range=40.0; got {result}"
    )
    # not avg-of-per-tool-IQR
    assert abs(result - 12.5) > 1.0, "Should not be avg of per-tool IQR"
    # not global range
    assert abs(result - 40.0) > 1.0, "Should not be global range (max-min)"


def test_consistent_with_global_latency_percentile() -> None:
    """Must equal p75_percentile - p25_percentile of pooled distribution."""
    store: dict = {}
    ts = _recent()
    for tool, lats in [("gi_c", [5.0, 15.0, 25.0, 35.0]), ("gi_d", [45.0, 80.0, 100.0])]:
        for lat in lats:
            _add(store, tool, lat, ts)

    iqr = get_windowed_global_latency_iqr_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    p75 = get_windowed_global_latency_percentile(75.0, WINDOW_MS, store=store, now_ms=NOW_MS)
    p25 = get_windowed_global_latency_percentile(25.0, WINDOW_MS, store=store, now_ms=NOW_MS)

    assert abs(iqr - (p75 - p25)) < 1e-9, (
        f"IQR={iqr} must equal p75({p75}) - p25({p25})={p75 - p25}"
    )


def test_single_tool_matches_per_tool_iqr() -> None:
    """With one tool, global IQR == per-tool IQR."""
    store: dict = {}
    ts = _recent()
    for lat in [10.0, 20.0, 30.0, 40.0, 50.0]:
        _add(store, "gi_e", lat, ts)

    global_iqr = get_windowed_global_latency_iqr_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    per_tool = get_windowed_tool_latency_iqr_ms("gi_e", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert abs(global_iqr - per_tool) < 1e-9, (
        f"single-tool: global_iqr={global_iqr} must equal per_tool_iqr={per_tool}"
    )


def test_empty_store_returns_zero() -> None:
    result = get_windowed_global_latency_iqr_ms(WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_old_calls_excluded() -> None:
    """Old latencies outside the window must not pollute fleet IQR."""
    store: dict = {}
    for _ in range(10):
        _add(store, "gi_f", 9999.0, _old())
    for lat in [10.0, 20.0, 30.0, 40.0, 50.0]:
        _add(store, "gi_f", lat, _recent())

    result = get_windowed_global_latency_iqr_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    # [10,20,30,40,50]: p75=40.0, p25=20.0, IQR=20.0
    assert abs(result - 20.0) < 1e-9, f"Old excluded; IQR([10,20,30,40,50])=20.0; got {result}"


def test_returns_float() -> None:
    store: dict = {}
    for lat in [10.0, 20.0, 30.0, 40.0]:
        _add(store, "gi_g", lat, _recent())
    result = get_windowed_global_latency_iqr_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float), f"Must return float; got {type(result)}"
