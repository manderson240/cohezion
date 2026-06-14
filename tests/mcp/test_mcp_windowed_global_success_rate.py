"""Item 988: get_windowed_global_success_rate() -- fleet-wide windowed success rate.

get_windowed_global_success_rate(window_ms, *, store=None, now_ms=None) -> float

Complement of item-987 global_error_rate.
global_success_rate = global_success_count / global_call_count (POOLED).
0.0 when no recent calls.
Property: global_success_rate + global_error_rate == 1.0 for non-empty window.

Supplemental discriminating tests (function pre-implemented from item 988 racing loop commit).

Discriminating tests:
  1. PRIMARY DISC.: tool_a 1/1 success + tool_b 0/3 successes
       -> pooled=1/4=0.25  (kills avg-of-per-tool-rates=(1.0+0.0)/2=0.5)
  2. All successes -> 1.0.
  3. No successes -> 0.0.
  4. success + error == 1.0.
  5. Empty store -> 0.0.
  6. Old calls excluded.
  7. Returns float.
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_global_error_rate,
    get_windowed_global_success_rate,
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


def test_pooled_not_avg_of_per_tool_rates_primary_discriminator() -> None:
    """PRIMARY DISC.: pooled success rate != avg(per-tool rates) when counts differ.

    tool_a: 1 call, 1 success  -> per-tool rate = 1.0
    tool_b: 3 calls, 0 successes -> per-tool rate = 0.0
    avg-of-per-tool-rates = (1.0 + 0.0) / 2 = 0.5  (WRONG naive impl)
    pooled = 1 success / 4 calls = 0.25              (CORRECT)

    Kills impl averaging per-tool success rates without weighting by call count.
    """
    store: dict = {}
    ts = _recent()
    _add(store, "tool_a", 10.0, ts, ok=True)  # 1 call, 1 success
    for _ in range(3):
        _add(store, "tool_b", 10.0, ts, ok=False)  # 3 calls, 0 successes

    result = get_windowed_global_success_rate(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 0.25) < 1e-9, (
        f"pooled=1/4=0.25; kills avg-of-rates=(1.0+0.0)/2=0.5; got {result}"
    )


def test_all_successes_returns_one() -> None:
    """All calls succeed fleet-wide -> success_rate=1.0."""
    store: dict = {}
    ts = _recent()
    for tool in ["a", "b"]:
        for _ in range(4):
            _add(store, tool, 10.0, ts, ok=True)
    result = get_windowed_global_success_rate(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 1.0) < 1e-9, f"All success -> 1.0; got {result}"


def test_no_successes_returns_zero() -> None:
    """All calls fail -> success_rate=0.0."""
    store: dict = {}
    ts = _recent()
    for _ in range(5):
        _add(store, "t", 10.0, ts, ok=False)
    result = get_windowed_global_success_rate(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 0.0, f"No successes -> 0.0; got {result}"


def test_success_rate_plus_error_rate_equals_one() -> None:
    """success_rate + error_rate == 1.0 for any non-empty window."""
    store: dict = {}
    ts = _recent()
    for _ in range(7):
        _add(store, "a", 10.0, ts, ok=True)
    for _ in range(3):
        _add(store, "b", 10.0, ts, ok=False)

    suc = get_windowed_global_success_rate(WINDOW_MS, store=store, now_ms=NOW_MS)
    err = get_windowed_global_error_rate(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert abs(suc + err - 1.0) < 1e-9, f"success={suc} + error={err} must = 1.0"


def test_empty_store_returns_zero() -> None:
    result = get_windowed_global_success_rate(WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_old_calls_excluded() -> None:
    """Successes outside the window do not count."""
    store: dict = {}
    for _ in range(100):
        _add(store, "t", 10.0, _old(), ok=True)  # old successes
    for _ in range(3):
        _add(store, "t", 10.0, _recent(), ok=True)
    _add(store, "t", 10.0, _recent(), ok=False)  # 3 success + 1 fail = 0.75

    result = get_windowed_global_success_rate(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 0.75) < 1e-9, f"Old successes excluded; 3/4=0.75; got {result}"


def test_returns_float() -> None:
    store: dict = {}
    _add(store, "t", 10.0, _recent(), ok=True)
    result = get_windowed_global_success_rate(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float), f"Must return float; got {type(result)}"
