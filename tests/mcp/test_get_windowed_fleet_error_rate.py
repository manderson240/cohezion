"""Item 1139: get_windowed_fleet_error_rate(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide error rate (fraction of failed calls) across all tools.
Returns float in [0.0, 1.0]. 0.0 for empty window (vacuous).
Thin composition: 1.0 - get_windowed_fleet_success_rate(...).

PRIMARY DISC. (fleet-pooled vs per-tool-avg):
  tool_a: 2 errors / 3 total -> rate=0.667
  tool_b: 0 errors / 2 total -> rate=0.0
  per-tool-avg = (0.667+0.0)/2 = 0.333
  fleet_error_rate = 2/5 = 0.4
  (PRIMARY DISC.: kills per-tool-avg=0.333≠0.4;
   correct: count_errors_all/count_all_pooled = 1 - success_rate).

Composition check: error_rate + success_rate == 1.0 always.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_error_rate,
    get_windowed_fleet_success_rate,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_error_rate_primary_discriminator() -> None:
    """PRIMARY DISC.: fleet_error_rate=0.4; kills per-tool-avg=0.333."""
    _reset()
    store = _make_store({
        "fer_a": [
            (_NOW - 900, 10.0, True),   # success
            (_NOW - 800, 20.0, False),  # error
            (_NOW - 700, 30.0, False),  # error
        ],
        "fer_b": [
            (_NOW - 600, 50.0, True),   # success
            (_NOW - 500, 60.0, True),   # success
        ],
    })
    # pooled: 2 errors / 5 total = 0.4; per-tool-avg = (2/3+0/2)/2 ≈ 0.333
    result = get_windowed_fleet_error_rate(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    assert abs(result - 0.4) < 1e-9, (
        f"fleet_error_rate=0.4; kills per-tool-avg≈0.333; got {result}"
    )


def test_fleet_error_rate_plus_success_rate_is_one() -> None:
    """Composition invariant: error_rate + success_rate == 1.0 always."""
    _reset()
    store = _make_store({
        "fer_comp_a": [
            (_NOW - 900, 10.0, True),
            (_NOW - 800, 20.0, False),
            (_NOW - 700, 30.0, False),
        ],
        "fer_comp_b": [
            (_NOW - 600, 50.0, True),
            (_NOW - 500, 60.0, True),
        ],
    })
    err = get_windowed_fleet_error_rate(_WIN, store=store, now_ms=_NOW)
    succ = get_windowed_fleet_success_rate(_WIN, store=store, now_ms=_NOW)
    assert abs(err + succ - 1.0) < 1e-12, f"err+succ={err+succ} != 1.0"


def test_fleet_error_rate_all_success_returns_zero() -> None:
    """All success records -> 0.0."""
    _reset()
    store = _make_store({
        "fer_ok_a": [(_NOW - float(d), 10.0, True) for d in [900, 800]],
        "fer_ok_b": [(_NOW - float(d), 20.0, True) for d in [700, 600]],
    })
    result = get_windowed_fleet_error_rate(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"all success -> 0.0; got {result}"


def test_fleet_error_rate_all_errors_returns_one() -> None:
    """All error records -> 1.0."""
    _reset()
    store = _make_store({
        "fer_err_a": [(_NOW - float(d), 10.0, False) for d in [900, 800]],
        "fer_err_b": [(_NOW - float(d), 20.0, False) for d in [700, 600]],
    })
    result = get_windowed_fleet_error_rate(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"all errors -> 1.0; got {result}"


def test_fleet_error_rate_empty_store_returns_zero() -> None:
    """Empty store -> 0.0 (vacuous no-error)."""
    _reset()
    result = get_windowed_fleet_error_rate(_WIN, store={}, now_ms=_NOW)
    assert abs(result) < 1e-9, f"empty -> 0.0; got {result}"


def test_fleet_error_rate_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0 (vacuous)."""
    _reset()
    store = _make_store({
        "fer_old": [(_NOW - _WIN - float(d), float(d), False) for d in [300, 200, 100]],
    })
    result = get_windowed_fleet_error_rate(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"no in-window calls -> 0.0; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fer_rt": [(_NOW - 400, 30.0, True), (_NOW - 200, 70.0, False)],
    })
    result = get_windowed_fleet_error_rate(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 0.5) < 1e-9
