"""Item 979: get_windowed_global_min_latency_ms() -- fleet-wide windowed minimum latency.

get_windowed_global_min_latency_ms(window_ms, *, store=None, now_ms=None) -> float

Pools ALL recent call latencies from all tools, returns the global minimum.
0.0 when no recent calls or store is empty.
Fleet-wide dual of get_windowed_tool_min_latency_ms() (item 974).

Discriminating tests:
  1. PRIMARY DISC.: tool_a [50, 30] + tool_b [10, 20] -> global_min=10.0
     (kills impl returning mean=27.5, global_max=50.0, or per-tool min of tool_a only).
  2. Single tool: result equals get_windowed_tool_min_latency_ms().
  3. Old calls excluded.
  4. Empty store -> 0.0.
  5. Returns float.
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_global_min_latency_ms,
    get_windowed_tool_min_latency_ms,
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


def test_global_min_across_all_tools_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a [50,30] + tool_b [10,20] -> min=10.0.

    Kills impl returning mean=27.5, max=50.0, or only tool_a's min=30.0.
    The global minimum must search across ALL tools.
    """
    store: dict = {}
    ts = _recent()
    _add(store, "tool_a", 50.0, ts)
    _add(store, "tool_a", 30.0, ts)
    _add(store, "tool_b", 10.0, ts)
    _add(store, "tool_b", 20.0, ts)

    result = get_windowed_global_min_latency_ms(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 10.0) < 1e-9, (
        f"min across tool_a[50,30]+tool_b[10,20]=10.0; kills mean=27.5,max=50.0; got {result}"
    )


def test_single_tool_matches_per_tool_min() -> None:
    """For a single tool, global min == per-tool min."""
    store: dict = {}
    ts = _recent()
    for lat in [50.0, 10.0, 30.0]:
        _add(store, "t", lat, ts)

    global_min = get_windowed_global_min_latency_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    per_tool = get_windowed_tool_min_latency_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert abs(global_min - per_tool) < 1e-9, (
        f"single-tool: global_min={global_min} must equal per-tool_min={per_tool}"
    )


def test_old_calls_excluded() -> None:
    """Old latencies outside the window must not affect global min."""
    store: dict = {}
    _add(store, "t", 0.001, _old())  # very small latency outside window
    _add(store, "t", 10.0, _recent())
    _add(store, "t", 20.0, _recent())

    result = get_windowed_global_min_latency_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 10.0) < 1e-9, f"Old call excluded; min([10,20])=10.0; got {result}"


def test_empty_store_returns_zero() -> None:
    result = get_windowed_global_min_latency_ms(WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_returns_float() -> None:
    store: dict = {}
    _add(store, "t", 25.0, _recent())
    result = get_windowed_global_min_latency_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float)
