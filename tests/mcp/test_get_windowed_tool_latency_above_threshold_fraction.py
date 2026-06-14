"""Item 1087: get_windowed_tool_latency_above_threshold_fraction(tool_name, window_ms, threshold_ms, *, store=None, now_ms=None) -> float
-- fraction of windowed calls where latency > threshold_ms.
0.0 for empty window. Range [0,1].

PRIMARY DISC.: 8 calls [10,80,90,20,70,85,95,15] threshold=50
  -> 5 above / 8 total = 0.625
  (PRIMARY DISC.: kills burst_count=2 -- runs not fraction;
   kills above-count=5 -- integer not fraction;
   correct fraction=0.625).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_above_threshold_fraction,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_above_threshold_fraction_primary_discriminator() -> None:
    """PRIMARY DISC.: [10,80,90,20,70,85,95,15] threshold=50 -> fraction=0.625.

    Kills burst_count=2 (runs, not fraction).
    Kills above-count=5 (integer, not fraction).
    Correct: 5/8=0.625.
    """
    _reset()
    lats = [10.0, 80.0, 90.0, 20.0, 70.0, 85.0, 95.0, 15.0]
    store = _make_store(
        {
            "atf_disc": [
                (_NOW - (len(lats) - 1 - i) * 50.0, lat, True) for i, lat in enumerate(lats)
            ],
        }
    )
    result = get_windowed_tool_latency_above_threshold_fraction(
        "atf_disc", _WIN, 50.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert abs(result - 0.625) < 1e-9, f"5/8=0.625; kills count=5; kills bursts=2; got {result}"


def test_above_threshold_fraction_all_above_returns_one() -> None:
    """All calls above threshold -> fraction=1.0."""
    _reset()
    store = _make_store(
        {
            "atf_all": [(_NOW - float(d), 100.0, True) for d in [300, 200, 100, 0]],
        }
    )
    result = get_windowed_tool_latency_above_threshold_fraction(
        "atf_all", _WIN, 50.0, store=store, now_ms=_NOW
    )
    assert abs(result - 1.0) < 1e-9, f"all above -> 1.0; got {result}"


def test_above_threshold_fraction_none_above_returns_zero() -> None:
    """No calls above threshold -> 0.0."""
    _reset()
    store = _make_store(
        {
            "atf_none": [(_NOW - float(d), 10.0, True) for d in [300, 200, 100, 0]],
        }
    )
    result = get_windowed_tool_latency_above_threshold_fraction(
        "atf_none", _WIN, 50.0, store=store, now_ms=_NOW
    )
    assert result == 0.0, f"none above -> 0.0; got {result}"


def test_above_threshold_fraction_empty_window_returns_zero() -> None:
    """Empty window -> 0.0."""
    _reset()
    assert (
        get_windowed_tool_latency_above_threshold_fraction(
            "no_tool", _WIN, 50.0, store={}, now_ms=_NOW
        )
        == 0.0
    )


def test_above_threshold_fraction_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "atf_old": [(_NOW - _WIN - 100, 200.0, True)] * 5,
        }
    )
    assert (
        get_windowed_tool_latency_above_threshold_fraction(
            "atf_old", _WIN, 50.0, store=store, now_ms=_NOW
        )
        == 0.0
    )


def test_above_threshold_fraction_threshold_boundary_exclusive() -> None:
    """Calls at exactly threshold are NOT counted (strictly > required)."""
    _reset()
    store = _make_store(
        {
            "atf_bound": [
                (_NOW - 200, 50.0, True),  # at threshold -- not above
                (_NOW - 100, 51.0, True),  # above
                (_NOW - 0, 50.0, True),  # at threshold -- not above
            ],
        }
    )
    result = get_windowed_tool_latency_above_threshold_fraction(
        "atf_bound", _WIN, 50.0, store=store, now_ms=_NOW
    )
    assert abs(result - (1.0 / 3.0)) < 1e-9, f"1/3 above; got {result}"


def test_above_threshold_fraction_in_range_zero_to_one() -> None:
    """Result must be in [0, 1]."""
    _reset()
    store = _make_store(
        {
            "atf_range": [
                (_NOW - float(d), float(v), True)
                for d, v in [(400, 10), (300, 80), (200, 90), (100, 20), (0, 70)]
            ],
        }
    )
    result = get_windowed_tool_latency_above_threshold_fraction(
        "atf_range", _WIN, 50.0, store=store, now_ms=_NOW
    )
    assert 0.0 <= result <= 1.0, f"fraction in [0,1]; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "atf_rt": [(_NOW - float(d), 100.0, True) for d in [300, 200, 100, 0]],
        }
    )
    assert isinstance(
        get_windowed_tool_latency_above_threshold_fraction(
            "atf_rt", _WIN, 50.0, store=store, now_ms=_NOW
        ),
        float,
    )
