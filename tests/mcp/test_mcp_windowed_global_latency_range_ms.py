"""Item 981: get_windowed_global_latency_range_ms() -- fleet-wide latency range.

get_windowed_global_latency_range_ms(window_ms, *, store=None, now_ms=None) -> float

Returns global_max - global_min pooled across all tools in the window.
0.0 when no recent calls, single call fleet-wide, or all latencies identical.
Composes get_windowed_global_max_latency_ms() - get_windowed_global_min_latency_ms().

Discriminating tests:
  1. PRIMARY DISC.: tool_a [10, 50] + tool_b [20, 90] -> range=80.0 (90-10)
     Kills impl returning per-tool range max (max(50-10,90-20)=70.0 not 80.0).
     Kills impl returning max=90.0 alone, min=10.0 alone, or mean=42.5.
  2. Single call fleet-wide -> 0.0.
  3. All-same latencies -> 0.0.
  4. Old calls excluded.
  5. Empty store -> 0.0.
  6. Returns float.
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_global_latency_range_ms,
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


def test_global_range_not_per_tool_range_primary_discriminator() -> None:
    """PRIMARY DISC.: global range = global_max - global_min, NOT max(per-tool ranges).

    tool_a: [10, 50]  -> per-tool range = 40.0
    tool_b: [20, 90]  -> per-tool range = 70.0
    max(per-tool ranges) = 70.0  (WRONG naive impl)
    global_max - global_min = 90 - 10 = 80.0  (CORRECT)

    Kills impl returning 70.0, 90.0 alone, 10.0 alone, or mean=42.5.
    """
    store: dict = {}
    ts = _recent()
    _add(store, "tool_a", 10.0, ts)
    _add(store, "tool_a", 50.0, ts)
    _add(store, "tool_b", 20.0, ts)
    _add(store, "tool_b", 90.0, ts)

    result = get_windowed_global_latency_range_ms(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 80.0) < 1e-9, (
        f"global range=90-10=80.0; kills per-tool-range-max=70.0; got {result}"
    )


def test_single_call_fleet_wide_returns_zero() -> None:
    """Single observation has no range."""
    store: dict = {}
    _add(store, "t", 42.0, _recent())
    result = get_windowed_global_latency_range_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 0.0, f"Single call -> range=0.0; got {result}"


def test_all_same_latencies_returns_zero() -> None:
    """All latencies equal -> range=0.0."""
    store: dict = {}
    ts = _recent()
    for tool in ["a", "b", "c"]:
        for _ in range(3):
            _add(store, tool, 25.0, ts)
    result = get_windowed_global_latency_range_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 0.0, f"All same -> range=0.0; got {result}"


def test_old_calls_excluded() -> None:
    """Old latencies must not affect the global range."""
    store: dict = {}
    _add(store, "t", 0.001, _old())  # tiny outside window
    _add(store, "t", 99999.0, _old())  # huge outside window
    _add(store, "t", 10.0, _recent())
    _add(store, "t", 30.0, _recent())  # recent range = 20.0

    result = get_windowed_global_latency_range_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 20.0) < 1e-9, f"Old calls excluded; range([10,30])=20.0; got {result}"


def test_empty_store_returns_zero() -> None:
    result = get_windowed_global_latency_range_ms(WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_returns_float() -> None:
    store: dict = {}
    _add(store, "t", 5.0, _recent())
    _add(store, "t", 15.0, _recent())
    result = get_windowed_global_latency_range_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float)
