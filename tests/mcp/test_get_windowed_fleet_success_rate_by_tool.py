"""Item 1181: get_windowed_fleet_success_rate_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> float
-- per-tool success rate: fraction of calls where success == True.
Returns float in [0.0, 1.0]. 0.0 for unknown/empty tool (vacuous).

PRIMARY DISC.:
  tool_a=[T,T,F] (2/3 success) → success_rate_a = 2/3 ≈ 0.667
  tool_b=[F,F]   (0/2 success) → success_rate_b = 0.0
  fleet success_rate pools both (2/5 = 0.4)
  success_rate_a=0.667 kills success_rate_b=0.0; kills fleet_rate=0.4; kills always-0.
  Composition: success_rate_by_tool + error_rate_by_tool == 1.0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_success_rate_by_tool,
    get_windowed_fleet_error_rate_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_success_rate_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: success_rate_a=2/3 kills success_rate_b=0.0; kills fleet=0.4; kills always-0."""
    _reset()
    store = _make_store(
        {
            "fsrbt_a": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 20.0, True),
                (_NOW - 700, 30.0, False),
            ],
            "fsrbt_b": [
                (_NOW - 600, 100.0, False),
                (_NOW - 500, 200.0, False),
            ],
        }
    )
    result = get_windowed_fleet_success_rate_by_tool(_WIN, "fsrbt_a", store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    expected = 2.0 / 3.0
    assert abs(result - expected) < 1e-9, (
        f"success_rate_a=2/3; kills success_rate_b=0.0/fleet=0.4/always-0; got {result}"
    )


def test_fleet_success_rate_by_tool_composition_with_error_rate() -> None:
    """Composition: success_rate_by_tool + error_rate_by_tool == 1.0."""
    _reset()
    store = _make_store(
        {
            "fsrbt_comp": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 20.0, False),
                (_NOW - 700, 30.0, True),
                (_NOW - 600, 40.0, False),
            ],
        }
    )
    success = get_windowed_fleet_success_rate_by_tool(_WIN, "fsrbt_comp", store=store, now_ms=_NOW)
    error = get_windowed_fleet_error_rate_by_tool(_WIN, "fsrbt_comp", store=store, now_ms=_NOW)
    assert abs(success + error - 1.0) < 1e-9, f"success({success}) + error({error}) != 1.0"


def test_fleet_success_rate_by_tool_all_success() -> None:
    """All calls succeed → success_rate == 1.0."""
    _reset()
    store = _make_store(
        {
            "fsrbt_ok": [(_NOW - float(d), 10.0, True) for d in [900, 800, 700]],
        }
    )
    result = get_windowed_fleet_success_rate_by_tool(_WIN, "fsrbt_ok", store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"all success → 1.0; got {result}"


def test_fleet_success_rate_by_tool_none_succeed() -> None:
    """No calls succeed → success_rate == 0.0."""
    _reset()
    store = _make_store(
        {
            "fsrbt_none": [(_NOW - float(d), 50.0, False) for d in [900, 800, 700]],
        }
    )
    result = get_windowed_fleet_success_rate_by_tool(_WIN, "fsrbt_none", store=store, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_success_rate_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store(
        {
            "fsrbt_other": [(_NOW - 500, 10.0, True)],
        }
    )
    result = get_windowed_fleet_success_rate_by_tool(_WIN, "nonexistent", store=store, now_ms=_NOW)
    assert abs(result) < 1e-9
    assert isinstance(result, float)


def test_fleet_success_rate_by_tool_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_success_rate_by_tool(_WIN, "any_tool", store={}, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_success_rate_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store(
        {
            "fsrbt_old": [(_NOW - _WIN - float(d), 10.0, True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_success_rate_by_tool(_WIN, "fsrbt_old", store=store, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fsrbt_rt": [
                (_NOW - 400, 10.0, True),
                (_NOW - 300, 20.0, False),
            ],
        }
    )
    result = get_windowed_fleet_success_rate_by_tool(_WIN, "fsrbt_rt", store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 0.5) < 1e-9  # 1 out of 2 succeeds
