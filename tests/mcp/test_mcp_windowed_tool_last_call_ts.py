"""Item 1017: get_windowed_tool_last_call_ts() — timestamp of most-recent call in window.

get_windowed_tool_last_call_ts(tool_name, window_ms, *, store=None, now_ms=None) -> float | None

Highest ts_ms among recent records. None if no recent calls.
Dual of item-1016 (first_call_ts). Pair [first_ts, last_ts] gives window coverage.

Discriminating tests:
  1. PRIMARY DISC.: timestamps [_NOW-40, _NOW-20, _NOW-10] -> last_ts=_NOW-10
       (kills first_ts=_NOW-40; kills mean_ts=_NOW-23; correct max ts)
  2. OLD+RECENT MIX: old calls excluded; only recent calls contribute
  3. None when no recent calls
  4. Single call -> that call's ts
  5. Returns float (not int, not None when records exist)
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_tool_last_call_ts,
)

NOW_MS = 100_000.0
WINDOW_MS = 10_000.0
CUTOFF_MS = NOW_MS - WINDOW_MS


@pytest.fixture(autouse=True)
def _clean():
    _WINDOWED_TELEMETRY.clear()
    yield
    _WINDOWED_TELEMETRY.clear()


def _add(store: dict, tool: str, ts: float, ok: bool = True, lat: float = 10.0) -> None:
    store.setdefault(tool, []).append((ts, lat, ok))


def _old_ts() -> float:
    return NOW_MS - WINDOW_MS - 1_000.0


def test_max_not_min_not_mean_primary_discriminator() -> None:
    """PRIMARY DISC.: timestamps [_NOW-40, _NOW-20, _NOW-10] -> last_ts=_NOW-10.

    Kills impl returning first_ts=_NOW-40 (min).
    Kills impl returning mean_ts≈_NOW-23 (avg).
    """
    store: dict = {}
    ts_oldest = NOW_MS - 40.0
    ts_mid = NOW_MS - 20.0
    ts_newest = NOW_MS - 10.0
    for ts in [ts_oldest, ts_mid, ts_newest]:
        _add(store, "lts_t", ts)

    result = get_windowed_tool_last_call_ts("lts_t", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - ts_newest) < 1e-9, (
        f"last_ts=max={ts_newest}; kills min={ts_oldest} or mean; got {result}"
    )


def test_old_calls_excluded() -> None:
    """Old calls outside window must not be the last call."""
    store: dict = {}
    # Old call with early timestamp
    _add(store, "lts_old", _old_ts())
    # Recent call
    ts_recent = NOW_MS - 50.0
    _add(store, "lts_old", ts_recent)

    result = get_windowed_tool_last_call_ts("lts_old", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert result is not None
    assert abs(result - ts_recent) < 1e-9, f"Old excluded; last recent ts={ts_recent}; got {result}"
    assert result > CUTOFF_MS, "Returned ts must be inside the window"


def test_none_when_no_recent_calls() -> None:
    """No calls in window -> None (not 0.0, not float('inf'))."""
    result = get_windowed_tool_last_call_ts("no_such", WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result is None, f"Empty store -> None; got {result}"


def test_single_call_returns_its_ts() -> None:
    """Single call in window -> returns that call's timestamp."""
    store: dict = {}
    ts = NOW_MS - 100.0
    _add(store, "lts_one", ts)

    result = get_windowed_tool_last_call_ts("lts_one", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert result is not None
    assert abs(result - ts) < 1e-9, f"Single call -> its ts={ts}; got {result}"


def test_only_old_calls_returns_none() -> None:
    """All calls outside window -> None."""
    store: dict = {}
    for _ in range(5):
        _add(store, "lts_allold", _old_ts())

    result = get_windowed_tool_last_call_ts("lts_allold", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert result is None, f"All old -> None; got {result}"
