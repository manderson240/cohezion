"""Item 978: get_windowed_global_mean_latency_ms() -- fleet-wide windowed mean latency.

get_windowed_global_mean_latency_ms(window_ms, *, store=None, now_ms=None) -> float

Pools ALL recent call latencies from all tools, computes arithmetic mean.
0.0 when no recent calls or store is empty.

Discriminating tests:
  1. PRIMARY DISC.: tool_a [10] + tool_b [10, 10, 90] ->
     pooled mean = (10+10+10+90)/4 = 30.0
     per-tool-mean average = (10 + 36.67)/2 = 23.33 (WRONG -- kills naive per-tool impl).
     Kills impl averaging per-tool means (weights tools equally instead of by call count).
  2. Single tool: result equals get_windowed_tool_mean_latency_ms().
  3. Old calls excluded.
  4. Empty store -> 0.0.
  5. Returns float.
"""
from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_global_mean_latency_ms,
    get_windowed_tool_mean_latency_ms,
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


def test_pooled_mean_not_per_tool_average_primary_discriminator() -> None:
    """PRIMARY DISC.: pooled mean != per-tool-mean avg when group sizes differ.

    tool_a: [10]           -> per-tool mean = 10.0
    tool_b: [10, 10, 90]   -> per-tool mean = 36.67
    per-tool-mean avg      = (10 + 36.67) / 2 = 23.33  (WRONG naive impl)
    pooled mean            = (10+10+10+90) / 4 = 30.0   (CORRECT)

    Kills any impl that averages per-tool means rather than pooling all latencies.
    """
    store: dict = {}
    ts = _recent()
    _add(store, "tool_a", 10.0, ts)
    _add(store, "tool_b", 10.0, ts)
    _add(store, "tool_b", 10.0, ts)
    _add(store, "tool_b", 90.0, ts)

    result = get_windowed_global_mean_latency_ms(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 30.0) < 1e-9, (
        f"pooled([10,10,10,90])=30.0; per-tool-avg=(10+36.67)/2=23.33 (wrong); got {result}"
    )


def test_single_tool_matches_per_tool_mean() -> None:
    """For a single tool, global mean == per-tool mean."""
    store: dict = {}
    ts = _recent()
    for lat in [10.0, 20.0, 90.0]:
        _add(store, "t", lat, ts)

    global_mean = get_windowed_global_mean_latency_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    per_tool = get_windowed_tool_mean_latency_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert abs(global_mean - per_tool) < 1e-9, (
        f"single-tool: global_mean={global_mean} must equal per-tool={per_tool}"
    )


def test_old_calls_excluded() -> None:
    """Old latencies must not affect the global mean."""
    store: dict = {}
    _add(store, "t", 9999.0, _old())   # huge old latency
    _add(store, "t", 10.0, _recent())
    _add(store, "t", 30.0, _recent())  # recent mean = 20.0

    result = get_windowed_global_mean_latency_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 20.0) < 1e-9, f"Old call excluded; mean([10,30])=20.0; got {result}"


def test_empty_store_returns_zero() -> None:
    result = get_windowed_global_mean_latency_ms(WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_returns_float() -> None:
    store: dict = {}
    _add(store, "t", 25.0, _recent())
    result = get_windowed_global_mean_latency_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float)
