"""Item 1163: get_windowed_fleet_error_rate_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> float
-- per-tool error rate within the fleet store.
Returns float in [0.0, 1.0]. 1.0 for unknown tool (no calls = all-error vacuous).

PRIMARY DISC.:
  tool_a=[T,F,F] → error_rate_a=2/3≈0.667
  tool_b=[T,T]   → error_rate_b=0.0
  fleet error rate = 2/5 = 0.4
  tool_a rate=2/3 kills fleet_rate=2/5; kills tool_b=0.0; kills always-0.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_error_rate_by_tool,
    get_windowed_fleet_error_rate,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_error_rate_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a=2/3≈0.667 kills fleet=2/5=0.4 and tool_b=0.0."""
    _reset()
    store = _make_store({
        "erb_tool_a": [
            (_NOW - 900, 10.0, True),   # success
            (_NOW - 800, 20.0, False),  # error
            (_NOW - 700, 30.0, False),  # error
        ],
        "erb_tool_b": [
            (_NOW - 600, 40.0, True),   # success
            (_NOW - 500, 50.0, True),   # success
        ],
    })
    result_a = get_windowed_fleet_error_rate_by_tool(_WIN, "erb_tool_a", store=store, now_ms=_NOW)
    assert isinstance(result_a, float), f"expected float, got {type(result_a)}"
    expected_a = 2.0 / 3.0
    assert abs(result_a - expected_a) < 1e-9, (
        f"tool_a error_rate=2/3; kills fleet=2/5/tool_b=0; got {result_a}"
    )


def test_fleet_error_rate_by_tool_differs_from_fleet_rate() -> None:
    """Per-tool rate ≠ fleet rate (unequal tool sizes create asymmetry)."""
    _reset()
    store = _make_store({
        "erb_fleet_a": [
            (_NOW - 900, 10.0, True),
            (_NOW - 800, 20.0, False),
            (_NOW - 700, 30.0, False),
        ],
        "erb_fleet_b": [
            (_NOW - 600, 40.0, True),
            (_NOW - 500, 50.0, True),
        ],
    })
    tool_rate = get_windowed_fleet_error_rate_by_tool(_WIN, "erb_fleet_a", store=store, now_ms=_NOW)
    fleet_rate = get_windowed_fleet_error_rate(_WIN, store=store, now_ms=_NOW)
    # tool_a = 2/3 ≈ 0.667; fleet = 2/5 = 0.4 — must differ
    assert abs(tool_rate - fleet_rate) > 0.1, (
        f"per-tool({tool_rate}) should differ from fleet({fleet_rate})"
    )


def test_fleet_error_rate_by_tool_zero_errors() -> None:
    """Tool with all successes -> 0.0."""
    _reset()
    store = _make_store({
        "erb_ok": [(_NOW - float(d), 10.0, True) for d in [900, 800, 700]],
    })
    result = get_windowed_fleet_error_rate_by_tool(_WIN, "erb_ok", store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"all success -> 0.0; got {result}"


def test_fleet_error_rate_by_tool_all_errors() -> None:
    """Tool with all failures -> 1.0."""
    _reset()
    store = _make_store({
        "erb_all_fail": [(_NOW - float(d), 10.0, False) for d in [900, 800, 700]],
    })
    result = get_windowed_fleet_error_rate_by_tool(_WIN, "erb_all_fail", store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"all fail -> 1.0; got {result}"


def test_fleet_error_rate_by_tool_unknown_tool_returns_one() -> None:
    """Unknown tool_name -> 1.0 (vacuous: no calls = no successes)."""
    _reset()
    store = _make_store({
        "erb_other": [(_NOW - 500, 10.0, True)],
    })
    result = get_windowed_fleet_error_rate_by_tool(_WIN, "nonexistent_tool", store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"unknown tool -> 1.0; got {result}"


def test_fleet_error_rate_by_tool_outside_window_returns_one() -> None:
    """All calls outside window for that tool -> 1.0 (no in-window data)."""
    _reset()
    store = _make_store({
        "erb_old": [(_NOW - _WIN - float(d), 10.0, True) for d in [300, 200, 100]],
    })
    result = get_windowed_fleet_error_rate_by_tool(_WIN, "erb_old", store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"outside window -> 1.0; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "erb_rt": [
            (_NOW - 400, 10.0, True),
            (_NOW - 300, 20.0, False),
        ],
    })
    result = get_windowed_fleet_error_rate_by_tool(_WIN, "erb_rt", store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 0.5) < 1e-9
