"""Item 961: get_windowed_tool_telemetry_full() -- 6-key windowed per-tool profile.

get_windowed_tool_telemetry_full(tool_name, window_ms, *, store=None, now_ms=None) -> dict

Returns {call_count, error_count, error_rate, p50_ms, p95_ms, success_rate} (6 keys).
success_rate = 1 - error_rate.
All-zero dict with success_rate=1.0 for unknown tool or no recent calls.

Discriminating tests:
  1. PRIMARY DISC.: 5 calls, 2 errors -> exact 6-key dict; kills 4-key get_tool_windowed_stats
     (missing error_count + success_rate) and kills any impl omitting those keys.
  2. Exactly 6 keys (not 4, not 8).
  3. success_rate = 1 - error_rate (derived, not independent).
  4. Unknown tool -> all-zero + success_rate=1.0.
  5. No recent calls (only old) -> all-zero + success_rate=1.0.
  6. All successes -> error_count=0, error_rate=0.0, success_rate=1.0.
  7. Uses _WINDOWED_TELEMETRY singleton by default.
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_tool_telemetry_full,
)

NOW_MS = 100_000.0
WINDOW_MS = 10_000.0
_EXPECTED_KEYS = frozenset(
    {"call_count", "error_count", "error_rate", "p50_ms", "p95_ms", "success_rate"}
)


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


def test_six_key_profile_primary_discriminator() -> None:
    """PRIMARY DISC.: 5 calls with 2 errors -> exact 6-key dict.

    Kills any impl that returns only 4 keys (get_tool_windowed_stats schema).
    """
    store: dict = {}
    ts = _recent()
    for lat in [10.0, 20.0, 30.0]:
        _add(store, "tool_a", lat, ts, ok=True)
    for lat in [100.0, 200.0]:
        _add(store, "tool_a", lat, ts, ok=False)

    result = get_windowed_tool_telemetry_full("tool_a", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, dict)
    assert set(result.keys()) == _EXPECTED_KEYS, (
        f"Expected 6 keys {_EXPECTED_KEYS}; got {set(result.keys())}"
    )
    assert result["call_count"] == 5
    assert result["error_count"] == 2
    assert abs(result["error_rate"] - 2.0 / 5.0) < 1e-9, (
        f"error_rate=0.4 expected; got {result['error_rate']}"
    )
    assert abs(result["success_rate"] - 3.0 / 5.0) < 1e-9, (
        f"success_rate=0.6 expected; got {result['success_rate']}"
    )
    assert result["p50_ms"] > 0.0
    assert result["p95_ms"] > 0.0


def test_exactly_six_keys() -> None:
    """Exactly 6 keys -- not 4 (windowed_stats), not 8 (cumulative full)."""
    store: dict = {}
    _add(store, "t", 10.0, _recent())
    result = get_windowed_tool_telemetry_full("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert len(result) == 6, f"Expected exactly 6 keys; got {len(result)}: {set(result.keys())}"


def test_success_rate_equals_one_minus_error_rate() -> None:
    """success_rate must equal 1 - error_rate (derived, not independent)."""
    store: dict = {}
    _add(store, "t", 10.0, _recent(), ok=True)
    _add(store, "t", 10.0, _recent(), ok=False)
    result = get_windowed_tool_telemetry_full("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result["success_rate"] - (1.0 - result["error_rate"])) < 1e-9, (
        f"success_rate={result['success_rate']} != 1 - error_rate={result['error_rate']}"
    )


def test_unknown_tool_returns_zero_dict() -> None:
    """Unknown tool -> all-zero dict with success_rate=1.0."""
    result = get_windowed_tool_telemetry_full("nonexistent", WINDOW_MS, store={}, now_ms=NOW_MS)
    assert set(result.keys()) == _EXPECTED_KEYS
    assert result["call_count"] == 0
    assert result["error_count"] == 0
    assert result["error_rate"] == 0.0
    assert result["success_rate"] == 1.0
    assert result["p50_ms"] == 0.0
    assert result["p95_ms"] == 0.0


def test_no_recent_calls_returns_zero_dict() -> None:
    """All calls outside window -> same as unknown tool."""
    store: dict = {}
    _add(store, "t", 50.0, _old())  # too old
    result = get_windowed_tool_telemetry_full("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result["call_count"] == 0
    assert result["success_rate"] == 1.0


def test_all_successes_zero_error_count() -> None:
    """All successful calls -> error_count=0, error_rate=0.0, success_rate=1.0."""
    store: dict = {}
    for lat in [5.0, 10.0, 15.0]:
        _add(store, "t", lat, _recent(), ok=True)
    result = get_windowed_tool_telemetry_full("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result["error_count"] == 0
    assert result["error_rate"] == 0.0
    assert result["success_rate"] == 1.0
    assert result["call_count"] == 3


def test_uses_windowed_telemetry_singleton() -> None:
    """Default store= uses _WINDOWED_TELEMETRY."""
    _WINDOWED_TELEMETRY["my_tool"] = [
        (NOW_MS - 5_000.0, 25.0, True),
        (NOW_MS - 5_000.0, 75.0, False),
    ]
    result = get_windowed_tool_telemetry_full("my_tool", WINDOW_MS, now_ms=NOW_MS)
    assert result["call_count"] == 2
    assert result["error_count"] == 1
