"""Item 1138: get_windowed_fleet_success_rate(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide success rate (fraction of successful calls) across all tools.
Returns float in [0.0, 1.0]. 1.0 for empty window (vacuous).

PRIMARY DISC. (fleet-pooled vs per-tool-avg):
  tool_a: 1 success / 3 total -> rate=0.333
  tool_b: 2 success / 2 total -> rate=1.0
  per-tool-avg = (0.333+1.0)/2 = 0.667
  fleet_success_rate = (1+2)/(3+2) = 3/5 = 0.6
  (PRIMARY DISC.: kills per-tool-avg=0.667≠0.6;
   correct: count_success_all/count_all_pooled, return float=0.6).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_success_rate,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_success_rate_primary_discriminator() -> None:
    """PRIMARY DISC.: fleet_rate=0.6; kills per-tool-avg=0.667."""
    _reset()
    store = _make_store(
        {
            "fsr_a": [
                (_NOW - 900, 10.0, True),  # success
                (_NOW - 800, 20.0, False),  # error
                (_NOW - 700, 30.0, False),  # error
            ],
            "fsr_b": [
                (_NOW - 600, 50.0, True),  # success
                (_NOW - 500, 60.0, True),  # success
            ],
        }
    )
    # pooled: 3/5 = 0.6; per-tool-avg = (1/3 + 2/2)/2 = (0.333+1.0)/2 ≈ 0.667
    result = get_windowed_fleet_success_rate(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    assert abs(result - 0.6) < 1e-9, f"fleet_rate=0.6; kills per-tool-avg≈0.667; got {result}"


def test_fleet_success_rate_all_success_returns_one() -> None:
    """All success records -> 1.0."""
    _reset()
    store = _make_store(
        {
            "fsr_ok_a": [(_NOW - float(d), 10.0, True) for d in [900, 800]],
            "fsr_ok_b": [(_NOW - float(d), 20.0, True) for d in [700, 600]],
        }
    )
    result = get_windowed_fleet_success_rate(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"all success -> 1.0; got {result}"


def test_fleet_success_rate_all_errors_returns_zero() -> None:
    """All error records -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fsr_err_a": [(_NOW - float(d), 10.0, False) for d in [900, 800]],
            "fsr_err_b": [(_NOW - float(d), 20.0, False) for d in [700, 600]],
        }
    )
    result = get_windowed_fleet_success_rate(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"all errors -> 0.0; got {result}"


def test_fleet_success_rate_empty_store_returns_one() -> None:
    """Empty store -> 1.0 (vacuous success)."""
    _reset()
    result = get_windowed_fleet_success_rate(_WIN, store={}, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"empty -> 1.0; got {result}"


def test_fleet_success_rate_outside_window_returns_one() -> None:
    """All calls outside window -> 1.0 (vacuous success)."""
    _reset()
    store = _make_store(
        {
            "fsr_old": [(_NOW - _WIN - float(d), float(d), False) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_success_rate(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"no in-window calls -> 1.0; got {result}"


def test_fleet_success_rate_in_range() -> None:
    """Result is always in [0.0, 1.0]."""
    _reset()
    store = _make_store(
        {
            "fsr_range": [
                (_NOW - 700, 10.0, True),
                (_NOW - 600, 20.0, False),
                (_NOW - 500, 30.0, True),
                (_NOW - 400, 40.0, False),
            ],
        }
    )
    result = get_windowed_fleet_success_rate(_WIN, store=store, now_ms=_NOW)
    assert 0.0 <= result <= 1.0
    assert abs(result - 0.5) < 1e-9  # 2 success / 4 total


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fsr_rt": [(_NOW - 400, 30.0, True), (_NOW - 200, 70.0, False)],
        }
    )
    result = get_windowed_fleet_success_rate(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 0.5) < 1e-9
