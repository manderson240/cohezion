"""Item 952: get_windowed_global_p95_ms() -- pooled p95 across all tools in window.

get_windowed_global_p95_ms(window_ms, *, store=None, now_ms=None) -> float

Pools all latency records from _WINDOWED_TELEMETRY within the last window_ms ms
across ALL tools and computes p95 on the combined list.  0.0 when no recent calls.

Discriminating tests:
  1. PRIMARY DISC.: pooled p95 differs from avg-of-per-tool-p95s when counts differ.
     tool A=[10]*3, tool B=[100]*1 -> pooled [10,10,10,100]; avg-p95s=(10+100)/2=55;
     correct pooled p95 = _percentile([10,10,10,100], 95) = 97.5 (not 55).
  2. Empty store -> 0.0.
  3. Only recent calls counted (old calls outside window excluded).
  4. Single tool: matches get_tool_windowed_p95_ms result.
  5. Returns float not int.
"""
from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import _WINDOWED_TELEMETRY, get_windowed_global_p95_ms

NOW_MS = 100_000.0
WINDOW_MS = 10_000.0


@pytest.fixture(autouse=True)
def _clean():
    _WINDOWED_TELEMETRY.clear()
    yield
    _WINDOWED_TELEMETRY.clear()


def _add(store: dict, tool: str, ts: float, lat: float, ok: bool = True) -> None:
    store.setdefault(tool, []).append((ts, lat, ok))


def test_pooled_not_avg_of_tool_p95s_primary_discriminator() -> None:
    """PRIMARY DISC.: pooled p95 ≠ naive avg of per-tool p95s when counts differ.

    tool_a: 3 calls at 10ms  -> p95=10
    tool_b: 1 call at 100ms -> p95=100
    avg-of-p95s = (10+100)/2 = 55 (WRONG impl)
    pooled [10,10,10,100]: p95 = 10 + 0.95*(100-10)*3 = 10+0.95*90=95.5?
    Let me think: sorted=[10,10,10,100], n=4; idx=0.95*3=2.85; floor=2, frac=0.85
    p95 = 10 + 0.85*(100-10) = 10 + 76.5 = 86.5.
    Either way it's NOT 55, killing the avg-of-p95 impl.
    """
    recent_ts = NOW_MS - 5_000.0
    store: dict = {}
    for _ in range(3):
        _add(store, "tool_a", recent_ts, 10.0)
    _add(store, "tool_b", recent_ts, 100.0)

    result = get_windowed_global_p95_ms(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float), f"Must return float; got {type(result)}"
    # Verify it's NOT the naive avg-of-p95s (55.0)
    assert abs(result - 55.0) > 1.0, (
        f"Got {result}: looks like naive avg-of-p95s=55; must pool latencies"
    )
    # Verify it's > 0 (there is data)
    assert result > 0.0, f"Must be > 0 with data; got {result}"


def test_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    result = get_windowed_global_p95_ms(WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0, f"Empty store -> 0.0; got {result}"


def test_old_calls_excluded_from_window() -> None:
    """Calls outside the window are excluded; result is 0.0 if all calls are old."""
    store: dict = {}
    old_ts = NOW_MS - WINDOW_MS - 1_000.0  # outside window
    _add(store, "tool_a", old_ts, 500.0)
    result = get_windowed_global_p95_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 0.0, f"Old calls excluded -> 0.0; got {result}"


def test_old_calls_do_not_inflate_result() -> None:
    """Mixed recent+old: old calls do not inflate the pooled p95."""
    store: dict = {}
    recent_ts = NOW_MS - 5_000.0
    old_ts = NOW_MS - WINDOW_MS - 1_000.0

    _add(store, "tool_a", recent_ts, 10.0)
    _add(store, "tool_a", old_ts, 10_000.0)  # should be excluded

    result = get_windowed_global_p95_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    # Only 1 recent call at 10ms -> p95 = 10.0
    assert result == 10.0, f"Old call must be excluded; got {result}"


def test_single_tool_matches_per_tool_p95() -> None:
    """Single tool: pooled global p95 matches get_tool_windowed_p95_ms."""
    from cohezion.mcp.compound_mcp_telemetry import get_tool_windowed_p95_ms

    store: dict = {}
    recent_ts = NOW_MS - 5_000.0
    for lat in [10.0, 30.0, 50.0, 70.0, 90.0]:
        _add(store, "solo", recent_ts, lat)

    global_result = get_windowed_global_p95_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    per_tool = get_tool_windowed_p95_ms("solo", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert abs(global_result - per_tool) < 1e-9, (
        f"Single tool: global={global_result}, per_tool={per_tool}; must match"
    )


def test_returns_float_not_int() -> None:
    """Return type must be float."""
    store: dict = {}
    _add(store, "t", NOW_MS - 5_000.0, 100.0)
    result = get_windowed_global_p95_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float), f"Must be float; got {type(result)}"


def test_uses_windowed_telemetry_by_default() -> None:
    """Without store kwarg, uses the global _WINDOWED_TELEMETRY singleton."""
    _WINDOWED_TELEMETRY["default_tool"] = [(NOW_MS - 5_000.0, 42.0, True)]
    result = get_windowed_global_p95_ms(WINDOW_MS, now_ms=NOW_MS)
    assert result == 42.0, f"Must read _WINDOWED_TELEMETRY by default; got {result}"
