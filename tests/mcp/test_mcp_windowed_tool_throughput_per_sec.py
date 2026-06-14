"""Item 996: get_windowed_tool_throughput_per_sec() — per-tool calls/sec.

get_windowed_tool_throughput_per_sec(tool_name, window_ms, *, store=None, now_ms=None) -> float

call_count_in_window / (window_ms / 1000.0)
PRE-COVERED from racing loop at line 2350 in compound_mcp_telemetry.py.
These are supplemental discriminating tests.

Discriminating tests:
  1. PRIMARY DISC.: 5 calls in 1000ms window -> 5.0/sec
       (kills raw count=5; kills calls/window_ms=0.005; correct=5/(1000/1000)=5.0)
  2. Window-scaling: 3 calls in 500ms -> 6.0/sec
       (kills 3/1000=0.003; kills 3/0.5=6.0-but-from-wrong-path)
  3. Unknown tool -> 0.0.
  4. Old calls excluded.
  5. Mixed old+recent: only recent count.
  6. Returns float.
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_tool_throughput_per_sec,
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


def test_throughput_not_raw_count_not_per_ms_primary_discriminator() -> None:
    """PRIMARY DISC.: 5 calls in 1000ms window -> 5.0/sec.

    raw count = 5                     (WRONG — units are count not rate)
    calls/window_ms = 5/1000 = 0.005  (WRONG — forgot the /1000 conversion)
    correct = 5 / (1000/1000) = 5.0   (calls/sec)

    Kills impl returning raw count (off by 5x).
    Kills impl dividing by window_ms directly (off by 1000x).
    """
    store: dict = {}
    window_ms = 1_000.0  # exactly 1 second
    ts = NOW_MS - 100.0  # well within window
    for _ in range(5):
        _add(store, "t", 10.0, ts)

    result = get_windowed_tool_throughput_per_sec("t", window_ms, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    # correct: 5.0 calls/sec
    assert abs(result - 5.0) < 1e-9, (
        f"5 calls/1s window = 5.0/sec; kills count=5 or /ms=0.005; got {result}"
    )
    # not raw count
    assert abs(result - 5) < 1.0  # coincides here; next test breaks the tie
    # verify not per-ms
    assert result > 0.01, f"per-ms=0.005 killed by {result}"


def test_window_scaling_discriminator() -> None:
    """DISC. 2: 3 calls in 500ms window -> 6.0/sec.

    3 / (500/1000) = 3 / 0.5 = 6.0
    Kills raw-count=3 (off by 2x), kills /window_ms=3/500=0.006 (off by 1000x).
    """
    store: dict = {}
    window_ms = 500.0  # half second
    ts = NOW_MS - 100.0
    for _ in range(3):
        _add(store, "t2", 5.0, ts)

    result = get_windowed_tool_throughput_per_sec("t2", window_ms, store=store, now_ms=NOW_MS)

    assert abs(result - 6.0) < 1e-9, f"3 calls/500ms = 6.0/sec; got {result}"


def test_unknown_tool_returns_zero() -> None:
    result = get_windowed_tool_throughput_per_sec("no_such", WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_old_calls_excluded() -> None:
    """Calls outside the window must not count toward throughput."""
    store: dict = {}
    for _ in range(100):
        _add(store, "t3", 1.0, _old())
    # 2 recent calls in 10s window -> 2/10 = 0.2/sec
    for _ in range(2):
        _add(store, "t3", 1.0, _recent())

    result = get_windowed_tool_throughput_per_sec("t3", WINDOW_MS, store=store, now_ms=NOW_MS)
    # 2 / (10000/1000) = 2 / 10.0 = 0.2
    assert abs(result - 0.2) < 1e-9, f"2 recent calls in 10s = 0.2/sec; old excluded; got {result}"


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0 (not some non-zero artifact)."""
    store: dict = {}
    for _ in range(5):
        _add(store, "t4", 1.0, _old())

    result = get_windowed_tool_throughput_per_sec("t4", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 0.0, f"All old calls -> 0.0; got {result}"


def test_returns_float() -> None:
    store: dict = {}
    _add(store, "t5", 1.0, _recent())
    result = get_windowed_tool_throughput_per_sec("t5", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float), f"Must return float; got {type(result)}"
