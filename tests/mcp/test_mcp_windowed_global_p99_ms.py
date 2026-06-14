"""Item 993: get_windowed_global_p99_ms() -- fleet-wide windowed p99 latency.

get_windowed_global_p99_ms(window_ms, *, store=None, now_ms=None) -> float

Pools ALL recent latencies from all tools and computes the 99th percentile.
Fleet-wide dual of get_windowed_tool_p99_ms (item 992).
0.0 when no recent calls.
Consistent with get_windowed_global_latency_percentile(99.0, ...).

Discriminating tests:
  1. PRIMARY DISC.: tool_a [10,50] + tool_b [20,30]
       -> pooled [10,20,30,50], idx=0.99*3=2.97, p99=30+0.97*(50-30)=49.4
       (kills avg-of-per-tool-p99=39.75; kills max-per-tool-p99=49.6).
  2. Consistent with get_windowed_global_latency_percentile(99.0, ...).
  3. Single tool: global p99 == per-tool p99.
  4. Empty store -> 0.0.
  5. Old calls excluded.
  6. Returns float.
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_global_latency_percentile,
    get_windowed_global_p99_ms,
    get_windowed_tool_p99_ms,
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


def test_pooled_p99_not_avg_not_max_per_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: pooled p99 != avg(per-tool p99) and != max(per-tool p99).

    tool_a: [10, 50]  -> p99_a = 10 + 0.99*(50-10) = 49.6
    tool_b: [20, 30]  -> p99_b = 20 + 0.99*(30-20) = 29.9
    avg-of-per-tool-p99 = (49.6 + 29.9) / 2 = 39.75  (WRONG)
    max-of-per-tool-p99 = 49.6                         (WRONG)
    pooled [10,20,30,50]: idx=0.99*3=2.97, p99=30+0.97*20=49.4  (CORRECT)

    Kills impl averaging per-tool p99.
    Kills impl taking max per-tool p99.
    """
    store: dict = {}
    ts = _recent()
    _add(store, "tool_a", 10.0, ts)
    _add(store, "tool_a", 50.0, ts)
    _add(store, "tool_b", 20.0, ts)
    _add(store, "tool_b", 30.0, ts)

    result = get_windowed_global_p99_ms(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 49.4) < 1e-9, (
        f"pooled p99=49.4; kills avg=39.75 or max-per-tool=49.6; got {result}"
    )


def test_consistent_with_global_latency_percentile() -> None:
    """Must equal get_windowed_global_latency_percentile(99.0, ...)."""
    store: dict = {}
    ts = _recent()
    for tool, lats in [("a", [5.0, 15.0, 25.0]), ("b", [35.0, 45.0, 80.0, 200.0])]:
        for lat in lats:
            _add(store, tool, lat, ts)

    shortcut = get_windowed_global_p99_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    full = get_windowed_global_latency_percentile(99.0, WINDOW_MS, store=store, now_ms=NOW_MS)

    assert abs(shortcut - full) < 1e-9, (
        f"shortcut={shortcut} must equal global_latency_percentile(99)={full}"
    )


def test_single_tool_matches_per_tool_p99() -> None:
    """With one tool, global p99 == per-tool p99."""
    store: dict = {}
    ts = _recent()
    for lat in [10.0, 20.0, 30.0, 40.0, 50.0]:
        _add(store, "t", lat, ts)

    global_p99 = get_windowed_global_p99_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    per_tool = get_windowed_tool_p99_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert abs(global_p99 - per_tool) < 1e-9, (
        f"single-tool: global_p99={global_p99} must equal per_tool_p99={per_tool}"
    )


def test_empty_store_returns_zero() -> None:
    result = get_windowed_global_p99_ms(WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_old_calls_excluded() -> None:
    """Huge old latencies must not pollute fleet p99."""
    store: dict = {}
    for _ in range(10):
        _add(store, "t", 9999.0, _old())
    for lat in [10.0, 20.0, 30.0, 40.0, 50.0]:
        _add(store, "t", lat, _recent())

    result = get_windowed_global_p99_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 49.6) < 1e-9, (
        f"Old excluded; single-tool [10,20,30,40,50] p99=49.6; got {result}"
    )


def test_returns_float() -> None:
    store: dict = {}
    _add(store, "t", 42.0, _recent())
    result = get_windowed_global_p99_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float), f"Must return float; got {type(result)}"
