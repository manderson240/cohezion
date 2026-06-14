"""Item 1020: get_windowed_global_latency_sum_ms() — fleet-wide latency sum.

get_windowed_global_latency_sum_ms(window_ms, *, store=None, now_ms=None) -> float

Pools ALL tool latencies in the window. 0.0 for empty.
Enables fleet mean: fleet_mean = global_sum / global_call_count.
Fleet-wide dual of item-1019 (per-tool sum).

Discriminating tests:
  1. PRIMARY DISC.: tool_a [10,50] + tool_b [200,300] -> 560.0
       (kills per-tool-a=60.0; kills per-tool-b=500.0; correct pooled sum)
  2. Empty store -> 0.0 (not exception, not None)
  3. Old calls excluded from sum
  4. Single tool -> sum equals per-tool sum
  5. Returns float (not int)
  6. Mixed old/recent: only recent latencies contribute
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_global_latency_sum_ms,
)

NOW_MS = 100_000.0
WINDOW_MS = 10_000.0
CUTOFF_MS = NOW_MS - WINDOW_MS


@pytest.fixture(autouse=True)
def _clean():
    _WINDOWED_TELEMETRY.clear()
    yield
    _WINDOWED_TELEMETRY.clear()


def _add(store: dict, tool: str, ts: float, lat: float, ok: bool = True) -> None:
    store.setdefault(tool, []).append((ts, lat, ok))


def _recent(offset: float = 0.0) -> float:
    return NOW_MS - 500.0 + offset


def _old() -> float:
    return NOW_MS - WINDOW_MS - 1_000.0


def test_pooled_sum_not_per_tool_sum_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a [10,50] + tool_b [200,300] -> 560.0.

    Kills impl returning per-tool-a sum = 60.0.
    Kills impl returning per-tool-b sum = 500.0.
    Kills impl returning max-tool-sum = 500.0.
    """
    store: dict = {}
    _add(store, "gls_a", _recent(0.0), 10.0)
    _add(store, "gls_a", _recent(1.0), 50.0)
    _add(store, "gls_b", _recent(2.0), 200.0)
    _add(store, "gls_b", _recent(3.0), 300.0)

    result = get_windowed_global_latency_sum_ms(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 560.0) < 1e-9, (
        f"pooled_sum=560.0; kills per-tool-a=60.0 or per-tool-b=500.0; got {result}"
    )


def test_empty_store_returns_zero() -> None:
    """Empty store -> 0.0 (not None, not exception)."""
    result = get_windowed_global_latency_sum_ms(WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0, f"Empty store -> 0.0; got {result}"
    assert isinstance(result, float), f"Must return float; got {type(result)}"


def test_old_calls_excluded_from_sum() -> None:
    """Old calls outside window must not contribute to sum."""
    store: dict = {}
    # Old call with large latency — must NOT appear in sum
    _add(store, "gls_old", _old(), 9999.0)
    # Recent calls
    _add(store, "gls_old", _recent(0.0), 100.0)
    _add(store, "gls_old", _recent(1.0), 200.0)

    result = get_windowed_global_latency_sum_ms(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert abs(result - 300.0) < 1e-9, f"Old excluded; recent sum=300.0; got {result}"


def test_single_tool_matches_per_tool_sum() -> None:
    """Single-tool global sum must equal per-tool sum."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_tool_latency_sum_ms

    store: dict = {}
    for lat in [15.0, 25.0, 35.0, 45.0]:
        _add(store, "gls_single", _recent(lat), lat)

    global_sum = get_windowed_global_latency_sum_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    per_tool_sum = get_windowed_tool_latency_sum_ms(
        "gls_single", WINDOW_MS, store=store, now_ms=NOW_MS
    )

    assert abs(global_sum - per_tool_sum) < 1e-9, (
        f"Single tool: global={global_sum} must equal per-tool={per_tool_sum}"
    )


def test_returns_float_not_int() -> None:
    """Return type must be float even for integer-valued latencies."""
    store: dict = {}
    _add(store, "gls_rt", _recent(0.0), 100.0)

    result = get_windowed_global_latency_sum_ms(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float), f"Must return float; got {type(result)}"


def test_all_old_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    store: dict = {}
    for _ in range(5):
        _add(store, "gls_allold", _old(), 500.0)

    result = get_windowed_global_latency_sum_ms(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert result == 0.0, f"All old -> 0.0; got {result}"


def test_three_tools_pooled() -> None:
    """Three tools: global sum = sum of all per-tool sums."""
    store: dict = {}
    _add(store, "t1", _recent(0.0), 100.0)
    _add(store, "t2", _recent(1.0), 200.0)
    _add(store, "t3", _recent(2.0), 400.0)

    result = get_windowed_global_latency_sum_ms(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert abs(result - 700.0) < 1e-9, f"3 tools: 100+200+400=700.0; got {result}"
