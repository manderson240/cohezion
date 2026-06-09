"""Item 1152: get_windowed_fleet_success_count(window_ms, *, store=None, now_ms=None) -> int
-- fleet-wide count of successful (success=True) calls in the window.
Returns int.  0 for empty window.

PRIMARY DISC.:
  tool_a = [T, F, F] (1 success), tool_b = [T, T] (2 successes)
  fleet success_count = 3
  kills error_count=2; kills total_count=5; kills always-0.
  Composition invariant: success_count + error_count == total_count.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_success_count,
    get_windowed_fleet_error_count,
    get_windowed_fleet_latency_count,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_success_count_primary_discriminator() -> None:
    """PRIMARY DISC.: success_count=3; kills error_count=2, total_count=5, always-0."""
    _reset()
    store = _make_store({
        "fsc_a": [
            (_NOW - 900, 10.0, True),   # success
            (_NOW - 800, 20.0, False),  # failure
            (_NOW - 700, 30.0, False),  # failure
        ],
        "fsc_b": [
            (_NOW - 600, 40.0, True),   # success
            (_NOW - 500, 50.0, True),   # success
        ],
    })
    result = get_windowed_fleet_success_count(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, int), f"expected int, got {type(result)}"
    assert result == 3, (
        f"success_count=3 (kills error_count=2, total=5, always-0); got {result}"
    )


def test_fleet_success_count_plus_error_count_equals_total() -> None:
    """Composition invariant: success_count + error_count == total_count."""
    _reset()
    store = _make_store({
        "fsc_comp_a": [
            (_NOW - 900, 10.0, True),
            (_NOW - 800, 20.0, False),
        ],
        "fsc_comp_b": [
            (_NOW - 700, 30.0, True),
            (_NOW - 600, 40.0, False),
            (_NOW - 500, 50.0, True),
        ],
    })
    successes = get_windowed_fleet_success_count(_WIN, store=store, now_ms=_NOW)
    errors = get_windowed_fleet_error_count(_WIN, store=store, now_ms=_NOW)
    total = get_windowed_fleet_latency_count(_WIN, store=store, now_ms=_NOW)
    assert successes + errors == total, (
        f"success({successes}) + error({errors}) = {successes+errors} != total({total})"
    )


def test_fleet_success_count_all_successful() -> None:
    """All calls succeed -> success_count == total_count."""
    _reset()
    store = _make_store({
        "fsc_ok": [(_NOW - float(d), 10.0, True) for d in [900, 800, 700, 600]],
    })
    result = get_windowed_fleet_success_count(_WIN, store=store, now_ms=_NOW)
    assert result == 4, f"all succeed -> 4; got {result}"


def test_fleet_success_count_all_failed_returns_zero() -> None:
    """All calls fail -> success_count == 0."""
    _reset()
    store = _make_store({
        "fsc_fail": [(_NOW - float(d), 10.0, False) for d in [900, 800, 700]],
    })
    result = get_windowed_fleet_success_count(_WIN, store=store, now_ms=_NOW)
    assert result == 0


def test_fleet_success_count_empty_store_returns_zero() -> None:
    """Empty store -> 0."""
    _reset()
    result = get_windowed_fleet_success_count(_WIN, store={}, now_ms=_NOW)
    assert result == 0
    assert isinstance(result, int)


def test_fleet_success_count_outside_window_returns_zero() -> None:
    """All calls outside window -> 0."""
    _reset()
    store = _make_store({
        "fsc_old": [(_NOW - _WIN - float(d), 10.0, True) for d in [300, 200, 100]],
    })
    result = get_windowed_fleet_success_count(_WIN, store=store, now_ms=_NOW)
    assert result == 0


def test_returns_int_type() -> None:
    """Return type is int."""
    _reset()
    store = _make_store({
        "fsc_rt": [
            (_NOW - 400, 10.0, True),
            (_NOW - 300, 20.0, False),
            (_NOW - 200, 30.0, True),
        ],
    })
    result = get_windowed_fleet_success_count(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, int), f"expected int, got {type(result).__name__}"
    assert result == 2  # 2 successes
