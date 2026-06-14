"""Item 977: get_windowed_tool_mean_latency_ms() -- windowed per-tool arithmetic mean.

get_windowed_tool_mean_latency_ms(tool_name, window_ms, *, store=None, now_ms=None)
    -> float

Returns the arithmetic mean of recent call latencies for tool_name.
0.0 for unknown tool or no recent calls.

Discriminating tests:
  1. PRIMARY DISC.: [10, 20, 90] -> mean=40.0, NOT p50=20.0
     (symmetric [10,20,30] would have mean==p50==20.0 -- NOT discriminating;
      [10, 20, 90] has p50=20.0 but mean=(10+20+90)/3=40.0 -- kills p50-returning impl).
  2. [10, 20, 30] symmetric case -> mean=20.0 (validates the base case).
  3. Unknown tool -> 0.0.
  4. Old calls excluded.
  5. Single call -> that value.
  6. Returns float.
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
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


def test_mean_differs_from_p50_primary_discriminator() -> None:
    """PRIMARY DISC.: [10, 20, 90] -> mean=40.0, NOT p50=20.0.

    This asymmetric fixture is the discriminating case:
    p50([10,20,90]) = 20.0 (middle value)
    mean([10,20,90]) = (10+20+90)/3 = 40.0
    Any impl returning p50 fails this test.
    """
    store: dict = {}
    ts = _recent()
    _add(store, "t", 10.0, ts)
    _add(store, "t", 20.0, ts)
    _add(store, "t", 90.0, ts)

    result = get_windowed_tool_mean_latency_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 40.0) < 1e-9, (
        f"mean([10,20,90])=40.0 (not p50=20.0); kills any p50-returning impl; got {result}"
    )


def test_symmetric_case_mean_equals_twenty() -> None:
    """[10, 20, 30]: mean = 20.0 (same as p50 here -- base case sanity check)."""
    store: dict = {}
    ts = _recent()
    for lat in [10.0, 20.0, 30.0]:
        _add(store, "t", lat, ts)

    result = get_windowed_tool_mean_latency_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 20.0) < 1e-9, f"mean([10,20,30])=20.0; got {result}"


def test_unknown_tool_returns_zero() -> None:
    result = get_windowed_tool_mean_latency_ms("no_such_tool", WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_old_calls_excluded() -> None:
    """Old calls outside the window must not affect the mean."""
    store: dict = {}
    _add(store, "t", 9999.0, _old())  # huge latency outside window
    _add(store, "t", 10.0, _recent())
    _add(store, "t", 30.0, _recent())  # mean of recent = 20.0

    result = get_windowed_tool_mean_latency_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 20.0) < 1e-9, f"Old call excluded; mean([10,30])=20.0; got {result}"


def test_single_call_returns_that_value() -> None:
    """Mean of a single element is that element."""
    store: dict = {}
    _add(store, "t", 42.0, _recent())

    result = get_windowed_tool_mean_latency_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 42.0) < 1e-9, f"Single call mean=42.0; got {result}"


def test_returns_float() -> None:
    store: dict = {}
    _add(store, "t", 100.0, _recent())
    result = get_windowed_tool_mean_latency_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float)
