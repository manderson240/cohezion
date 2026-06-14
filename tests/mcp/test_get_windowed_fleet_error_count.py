"""Item 1137: get_windowed_fleet_error_count(window_ms, *, store=None, now_ms=None) -> int
-- fleet-wide total error (success=False) call count across all tools.
0 for empty/all-success window. Returns int.

PRIMARY DISC. (fleet-error-count vs per-tool-avg):
  tool_a errors=2, tool_b errors=1
  per-tool-avg = (2+1)/2 = 1.5 (float, wrong type)
  max-per-tool = 2
  fleet_error_count = 2+1 = 3
  (PRIMARY DISC.: kills per-tool-avg=1.5; kills max-per-tool=2;
   correct: sum ALL error records, return int=3).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_error_count,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_error_count_primary_discriminator() -> None:
    """PRIMARY DISC.: fleet_error_count=3; kills per-tool-avg=1.5 and max-per-tool=2."""
    _reset()
    store = _make_store(
        {
            "ferr_a": [
                (_NOW - 900, 10.0, False),  # error
                (_NOW - 800, 20.0, True),  # success
                (_NOW - 700, 30.0, False),  # error
            ],
            "ferr_b": [
                (_NOW - 600, 50.0, False),  # error
                (_NOW - 500, 60.0, True),  # success
            ],
        }
    )
    result = get_windowed_fleet_error_count(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, int), f"expected int, got {type(result)}"
    assert result == 3, f"fleet_error_count=3; kills per-tool-avg=1.5, kills max=2; got {result}"


def test_fleet_error_count_all_success_returns_zero() -> None:
    """All success records -> 0 errors."""
    _reset()
    store = _make_store(
        {
            "ferr_ok_a": [(_NOW - float(d), 10.0, True) for d in [900, 800]],
            "ferr_ok_b": [(_NOW - float(d), 20.0, True) for d in [700, 600]],
        }
    )
    result = get_windowed_fleet_error_count(_WIN, store=store, now_ms=_NOW)
    assert result == 0


def test_fleet_error_count_empty_store_returns_zero() -> None:
    """Empty store -> 0."""
    _reset()
    result = get_windowed_fleet_error_count(_WIN, store={}, now_ms=_NOW)
    assert result == 0
    assert isinstance(result, int)


def test_fleet_error_count_outside_window_returns_zero() -> None:
    """All calls outside window -> 0."""
    _reset()
    store = _make_store(
        {
            "ferr_old": [(_NOW - _WIN - float(d), float(d), False) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_error_count(_WIN, store=store, now_ms=_NOW)
    assert result == 0


def test_fleet_error_count_window_boundary_exact() -> None:
    """Error at exactly cutoff boundary (ts == cutoff_ms) is included."""
    _reset()
    store = _make_store(
        {
            "ferr_bnd": [
                (_NOW - _WIN, 50.0, False),  # ts == cutoff, error -> included
                (_NOW - _WIN - 1, 99.0, False),  # ts < cutoff -> excluded
            ],
        }
    )
    result = get_windowed_fleet_error_count(_WIN, store=store, now_ms=_NOW)
    assert result == 1, f"boundary error included; expected 1; got {result}"


def test_fleet_error_count_mixed_window() -> None:
    """Mixed success/failure across tools with some outside window."""
    _reset()
    store = _make_store(
        {
            "ferr_mix_a": [
                (_NOW - 900, 10.0, False),  # in window, error
                (_NOW - _WIN - 100, 20.0, False),  # outside window, ignored
            ],
            "ferr_mix_b": [
                (_NOW - 500, 60.0, True),  # in window, success
                (_NOW - 400, 70.0, False),  # in window, error
                (_NOW - 300, 80.0, False),  # in window, error
            ],
        }
    )
    # in-window errors: ferr_mix_a=1, ferr_mix_b=2 → total=3
    result = get_windowed_fleet_error_count(_WIN, store=store, now_ms=_NOW)
    assert result == 3, f"expected 3; got {result}"


def test_returns_int_type() -> None:
    """Return type is int (not float)."""
    _reset()
    store = _make_store(
        {
            "ferr_rt": [(_NOW - 400, 30.0, False), (_NOW - 200, 70.0, False)],
        }
    )
    result = get_windowed_fleet_error_count(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, int), f"expected int, got {type(result).__name__}"
    assert result == 2
