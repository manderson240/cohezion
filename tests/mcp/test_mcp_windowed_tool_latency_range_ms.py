"""Item 976: get_windowed_tool_latency_range_ms() -- windowed per-tool latency range.

get_windowed_tool_latency_range_ms(tool_name, window_ms, *, store=None, now_ms=None)
    -> float

Returns max(latencies) - min(latencies) for recent calls.
0.0 for unknown tool, no recent calls, single call, or all-same latencies.
Composes get_windowed_tool_max_latency_ms() - get_windowed_tool_min_latency_ms().

Discriminating tests:
  1. PRIMARY DISC.: [50, 10, 30] -> range=40.0 (50-10)
     (kills impl returning max=50.0 alone; kills impl returning min=10.0; kills mean=30.0).
  2. Single call -> 0.0 (range of one element).
  3. All-same values -> 0.0.
  4. Unknown tool -> 0.0.
  5. Old calls excluded.
  6. Returns float.
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_tool_latency_range_ms,
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


def test_range_is_max_minus_min_primary_discriminator() -> None:
    """PRIMARY DISC.: [50, 10, 30] -> range=40.0 (max-min); kills max=50, min=10, mean=30."""
    store: dict = {}
    ts = _recent()
    _add(store, "t", 50.0, ts)
    _add(store, "t", 10.0, ts)
    _add(store, "t", 30.0, ts)

    result = get_windowed_tool_latency_range_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 40.0) < 1e-9, (
        f"range([50,10,30]) = 50-10 = 40.0; kills max alone or min alone; got {result}"
    )


def test_single_call_returns_zero() -> None:
    """A single data point has no range."""
    store: dict = {}
    _add(store, "t", 25.0, _recent())

    result = get_windowed_tool_latency_range_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 0.0, f"Single call -> range=0.0; got {result}"


def test_all_same_values_returns_zero() -> None:
    """Uniform latencies have zero range."""
    store: dict = {}
    ts = _recent()
    for _ in range(5):
        _add(store, "t", 15.0, ts)

    result = get_windowed_tool_latency_range_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 0.0, f"All same -> range=0.0; got {result}"


def test_unknown_tool_returns_zero() -> None:
    result = get_windowed_tool_latency_range_ms("no_such_tool", WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_old_calls_excluded() -> None:
    """Range computed from recent calls only; old extremes must not affect it."""
    store: dict = {}
    _add(store, "t", 0.001, _old())  # tiny latency outside window
    _add(store, "t", 99999.0, _old())  # huge latency outside window
    _add(store, "t", 10.0, _recent())
    _add(store, "t", 30.0, _recent())  # recent range = 30-10=20

    result = get_windowed_tool_latency_range_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 20.0) < 1e-9, f"Old calls excluded; recent=[10,30] range=20.0; got {result}"


def test_returns_float() -> None:
    store: dict = {}
    _add(store, "t", 5.0, _recent())
    _add(store, "t", 15.0, _recent())
    result = get_windowed_tool_latency_range_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float)
