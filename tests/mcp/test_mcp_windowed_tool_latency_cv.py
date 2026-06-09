"""Item 1012: get_windowed_tool_latency_cv() — per-tool coefficient of variation.

get_windowed_tool_latency_cv(tool_name, window_ms, *, store=None, now_ms=None) -> float

CV = stddev_ms / mean_ms — dimensionless ratio measuring relative spread.
High CV (>1) = chaotic; Low CV (<0.5) = tight/predictable.
0.0 for unknown tools, empty windows, single calls, or mean=0.

Discriminating tests:
  1. PRIMARY DISC.: lats [10,20,30,40,50] -> CV≈0.4714
       mean=30, stddev=sqrt(200)≈14.1421, CV=14.1421/30≈0.4714
       (kills raw_stddev=14.1421; kills raw_mean=30.0; correct CV≈0.4714)
  2. SINGLE CALL -> 0.0 (not inf, not stddev=0 error)
  3. Zero-mean guard: all-zero latencies -> 0.0 (not division by zero)
  4. Unknown tool -> 0.0
  5. Old calls excluded.
  6. Returns float.
"""
from __future__ import annotations

import math
import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_tool_latency_cv,
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


def test_cv_not_stddev_not_mean_primary_discriminator() -> None:
    """PRIMARY DISC.: lats [10,20,30,40,50] -> CV≈0.4714.

    mean=30.0
    population variance = ((−20)²+(−10)²+0²+10²+20²)/5 = 1000/5 = 200
    stddev = sqrt(200) ≈ 14.1421
    CV = 14.1421 / 30 ≈ 0.4714

    Kills impl returning raw_stddev=14.1421.
    Kills impl returning raw_mean=30.0.
    Kills impl returning variance=200.0.
    """
    store: dict = {}
    ts = _recent()
    for lat in [10.0, 20.0, 30.0, 40.0, 50.0]:
        _add(store, "cv_t", lat, ts)

    result = get_windowed_tool_latency_cv("cv_t", WINDOW_MS, store=store, now_ms=NOW_MS)

    expected = math.sqrt(200.0) / 30.0
    assert isinstance(result, float)
    assert abs(result - expected) < 1e-9, (
        f"CV=sqrt(200)/30={expected:.6f}; kills stddev=14.14 or mean=30.0; got {result}"
    )


def test_single_call_returns_zero() -> None:
    """Single call has no variance -> CV=0.0 (not inf or division error)."""
    store: dict = {}
    _add(store, "cv_one", 100.0, _recent())

    result = get_windowed_tool_latency_cv("cv_one", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert result == 0.0, f"Single call: CV=0.0; got {result}"


def test_uniform_latency_returns_zero() -> None:
    """Identical latencies: variance=0 -> stddev=0 -> CV=0.0."""
    store: dict = {}
    for _ in range(5):
        _add(store, "cv_uni", 50.0, _recent())

    result = get_windowed_tool_latency_cv("cv_uni", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert result == 0.0, f"Uniform latency: CV=0.0; got {result}"


def test_unknown_tool_returns_zero() -> None:
    result = get_windowed_tool_latency_cv("no_such_tool", WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_old_calls_excluded() -> None:
    """Old calls outside window must not affect CV."""
    store: dict = {}
    # Old high-variance calls: should not count
    for lat in [1.0, 9999.0]:
        _add(store, "cv_old", lat, _old())
    # Recent uniform calls: CV=0
    for _ in range(4):
        _add(store, "cv_old", 50.0, _recent())

    result = get_windowed_tool_latency_cv("cv_old", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert result == 0.0, f"Old excluded; recent uniform -> CV=0.0; got {result}"


def test_returns_float() -> None:
    store: dict = {}
    for lat in [10.0, 20.0, 30.0, 40.0, 50.0]:
        _add(store, "cv_rt", lat, _recent())
    result = get_windowed_tool_latency_cv("cv_rt", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float), f"Must return float; got {type(result)}"
