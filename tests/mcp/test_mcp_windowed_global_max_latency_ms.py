"""Item 980: get_windowed_global_max_latency_ms() -- fleet-wide windowed max latency.

get_windowed_global_max_latency_ms(window_ms, *, store=None, now_ms=None) -> float

Pools ALL recent call latencies from all tools, returns the global maximum.
0.0 when no recent calls or store is empty.
Fleet-wide dual of get_windowed_tool_max_latency_ms() (item 975).
Complement of get_windowed_global_min_latency_ms() (item 979).

Discriminating tests:
  1. PRIMARY DISC.: tool_a [10, 30] + tool_b [50, 20] -> global_max=50.0
     (kills impl returning min=10.0, mean=27.5, or per-tool max of tool_a=30.0).
  2. Single tool: result equals get_windowed_tool_max_latency_ms().
  3. Old calls excluded.
  4. Empty store -> 0.0.
  5. Returns float.
"""
from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_global_max_latency_ms,
    get_windowed_tool_max_latency_ms,
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


def test_global_max_across_all_tools_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a [10,30] + tool_b [50,20] -> max=50.0.

    Kills impl returning min=10.0, mean=27.5, or only tool_a's max=30.0.
    The global maximum must search across ALL tools.
    """
    store: dict = {}
    ts = _recent()
    _add(store, "tool_a", 10.0, ts)
    _add(store, "tool_a", 30.0, ts)
    _add(store, "tool_b", 50.0, ts)
    _add(store, "tool_b", 20.0, ts)

    result = get_windowed_global_max_latency_ms(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 50.0) < 1e-9, (
        f"max across tool_a[10,30]+tool_b[50,20]=50.0; kills min=10.0,mean=27.5; got {result}"
    )


def test_single_tool_matches_per_tool_max() -> None:
    """For a single tool, global max == per-tool max."""
    store: dict = {}
    ts = _recent()
    for lat in [10.0, 50.0, 30.0]:
        _add(store, "t", lat, ts)

    global_max = get_windowed_global_max_latency_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    per_tool = get_windowed_tool_max_latency_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert abs(global_max - per_tool) < 1e-9, (
        f"single-tool: global_max={global_max} must equal per-tool_max={per_tool}"
    )


def test_old_calls_excluded() -> None:
    """Old latencies outside the window must not affect global max."""
    store: dict = {}
    _add(store, "t", 99999.0, _old())  # huge old latency outside window
    _add(store, "t", 10.0, _recent())
    _add(store, "t", 30.0, _recent())  # recent max = 30.0

    result = get_windowed_global_max_latency_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 30.0) < 1e-9, f"Old call excluded; max([10,30])=30.0; got {result}"


def test_empty_store_returns_zero() -> None:
    result = get_windowed_global_max_latency_ms(WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_returns_float() -> None:
    store: dict = {}
    _add(store, "t", 25.0, _recent())
    result = get_windowed_global_max_latency_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float)
