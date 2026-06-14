"""Item 975: get_windowed_tool_max_latency_ms() -- windowed per-tool max latency.

get_windowed_tool_max_latency_ms(tool_name, window_ms, *, store=None, now_ms=None)
    -> float

Returns the maximum latency (ms) among recent calls for tool_name.
0.0 for unknown tool or no recent calls.
Failed calls (ok=False) are included in the max.

Discriminating tests:
  1. PRIMARY DISC.: [50, 10, 30] -> max=50.0
     (kills impl returning min=10.0, p50=30.0, mean=30.0, or first=50.0 from sorted).
  2. Unknown tool -> 0.0.
  3. Old calls excluded.
  4. Failed calls included in max.
  5. All-same values -> that value.
  6. Returns float.
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
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


def test_returns_max_not_min_or_mean_primary_discriminator() -> None:
    """PRIMARY DISC.: [50, 10, 30] -> max=50.0; kills min=10.0, p50=30.0, mean=30.0."""
    store: dict = {}
    ts = _recent()
    _add(store, "t", 50.0, ts)
    _add(store, "t", 10.0, ts)
    _add(store, "t", 30.0, ts)

    result = get_windowed_tool_max_latency_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 50.0) < 1e-9, (
        f"max([50,10,30])=50.0; kills min=10.0,p50=30.0,mean=30.0; got {result}"
    )


def test_unknown_tool_returns_zero() -> None:
    result = get_windowed_tool_max_latency_ms("no_such_tool", WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_old_calls_excluded() -> None:
    """Max must be computed from recent calls only."""
    store: dict = {}
    _add(store, "t", 9999.0, _old())  # huge latency outside window
    _add(store, "t", 20.0, _recent())  # only this one counts

    result = get_windowed_tool_max_latency_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 20.0) < 1e-9, f"Old call excluded; max of recent=[20.0]; got {result}"


def test_failed_calls_included_in_max() -> None:
    """Failed calls (ok=False) should still contribute to the max."""
    store: dict = {}
    ts = _recent()
    _add(store, "t", 5.0, ts, ok=True)
    _add(store, "t", 999.0, ts, ok=False)  # failed but highest latency

    result = get_windowed_tool_max_latency_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 999.0) < 1e-9, (
        f"Failed call with lat=999.0 must be included in max; got {result}"
    )


def test_all_same_values() -> None:
    """When all latencies are equal, max == that value."""
    store: dict = {}
    ts = _recent()
    for _ in range(5):
        _add(store, "t", 42.0, ts)

    result = get_windowed_tool_max_latency_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 42.0) < 1e-9, f"All 42.0 -> max=42.0; got {result}"


def test_returns_float() -> None:
    store: dict = {}
    _add(store, "t", 25.0, _recent())
    result = get_windowed_tool_max_latency_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float)
