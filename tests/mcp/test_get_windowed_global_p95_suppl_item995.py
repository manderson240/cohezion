"""Item 995: supplemental discriminating tests for get_windowed_global_p95_ms().

get_windowed_global_p95_ms(window_ms, *, store=None, now_ms=None) -> float

Function pre-exists at line 1138 (item 952).  These tests cover the
specific PRIMARY DISC. fixture from item 995's backlog entry, which
differs from the item 952 test in test_get_windowed_global_p95_ms.py.

PRIMARY DISC.:
  tool_a [10, 50] + tool_b [20, 30]
  -> pooled sorted [10, 20, 30, 50]
  idx = 0.95 * (4-1) = 2.85
  p95 = 30 + 0.85 * (50-30) = 30 + 17 = 47.0

  per-tool p95:
    tool_a: idx=0.95*1=0.95; 10+0.95*(50-10)=48.0
    tool_b: idx=0.95*1=0.95; 20+0.95*(30-20)=29.5
    avg-of-per-tool-p95 = (48.0+29.5)/2 = 38.75  (WRONG)
    max-per-tool-p95 = 48.0                        (WRONG)
    pooled p95 = 47.0                              (CORRECT)

Kills: avg-of-per-tool-p95=38.75; kills max-per-tool-p95=48.0.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_global_latency_percentile,
    get_windowed_global_p95_ms,
    get_windowed_tool_p95_ms,
)
import pytest

_NOW = 1_000_000.0
_WIN = 500.0


@pytest.fixture(autouse=True)
def _clean():
    _WINDOWED_TELEMETRY.clear()
    yield
    _WINDOWED_TELEMETRY.clear()


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def test_pooled_p95_not_avg_not_max_per_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: pooled p95=47.0 != avg-per-tool=38.75 != max-per-tool=48.0.

    tool_a [10, 50]: per-tool p95 = 10 + 0.95*(50-10) = 48.0
    tool_b [20, 30]: per-tool p95 = 20 + 0.95*(30-20) = 29.5
    avg-of-per-tool-p95 = (48.0+29.5)/2 = 38.75  -> WRONG
    max-per-tool-p95    = 48.0                    -> WRONG
    pooled [10,20,30,50]: idx=0.95*3=2.85; 30+0.85*20=47.0 -> CORRECT
    """
    store = _make_store({
        "g95s_a": [(_NOW - 10, 10.0, True), (_NOW - 10, 50.0, True)],
        "g95s_b": [(_NOW - 10, 20.0, True), (_NOW - 10, 30.0, True)],
    })
    result = get_windowed_global_p95_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    # pooled p95=47.0
    assert abs(result - 47.0) < 1e-9, (
        f"pooled p95=47.0; kills avg=38.75 or max-per-tool=48.0; got {result}"
    )
    # not avg-of-per-tool
    assert abs(result - 38.75) > 1.0
    # not max-per-tool
    assert abs(result - 48.0) > 0.5


def test_consistent_with_global_latency_percentile() -> None:
    """Must equal get_windowed_global_latency_percentile(95.0, ...)."""
    store = _make_store({
        "g95s_c": [(_NOW - 10, float(v), True) for v in [5, 15, 25, 35, 100]],
        "g95s_d": [(_NOW - 10, float(v), True) for v in [10, 20, 60]],
    })
    shortcut = get_windowed_global_p95_ms(_WIN, store=store, now_ms=_NOW)
    generic = get_windowed_global_latency_percentile(95.0, _WIN, store=store, now_ms=_NOW)
    assert abs(shortcut - generic) < 1e-9, (
        f"global_p95={shortcut} must equal global_latency_percentile(95)={generic}"
    )


def test_single_tool_matches_per_tool_p95() -> None:
    """With one tool, global p95 == per-tool p95."""
    store = _make_store({
        "g95s_e": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
    })
    global_p95 = get_windowed_global_p95_ms(_WIN, store=store, now_ms=_NOW)
    per_tool = get_windowed_tool_p95_ms("g95s_e", _WIN, store=store, now_ms=_NOW)
    assert abs(global_p95 - per_tool) < 1e-9, (
        f"single-tool: global_p95={global_p95} must equal per_tool_p95={per_tool}"
    )


def test_empty_store_returns_zero() -> None:
    assert get_windowed_global_p95_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_old_calls_excluded() -> None:
    """Calls outside the window must not affect fleet p95."""
    store = _make_store({
        "g95s_f": [(_NOW - _WIN - 100, 9999.0, True)] * 5
        + [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
    })
    result = get_windowed_global_p95_ms(_WIN, store=store, now_ms=_NOW)
    # [10,20,30,40,50]: idx=0.95*4=3.8; 40+0.8*(50-40)=48.0
    assert abs(result - 48.0) < 1e-9, (
        f"Old excluded; p95([10,20,30,40,50])=48.0; got {result}"
    )


def test_returns_float_type() -> None:
    store = _make_store({"g95s_g": [(_NOW - 10, float(v), True) for v in range(1, 6)]})
    assert isinstance(get_windowed_global_p95_ms(_WIN, store=store, now_ms=_NOW), float)
