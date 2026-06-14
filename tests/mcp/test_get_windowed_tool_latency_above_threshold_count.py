"""Item 1104: get_windowed_tool_latency_above_threshold_count(tool_name, window_ms, threshold_ms, *, store=None, now_ms=None) -> int
-- count of windowed calls with latency strictly > threshold_ms.
Returns int, not float. 0 for empty window.

PRIMARY DISC.: 10 calls lats=[10,20,...,100]ms, threshold=50ms -> count=5
  (calls with lat 60,70,80,90,100 > 50ms; strictly >)
  (PRIMARY DISC.: kills fraction=0.5 (float not count);
   kills count>=threshold: lat=50 included -> count=6 not 5;
   correct: strictly > gives count=5).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_above_threshold_count,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_above_threshold_count_primary_discriminator() -> None:
    """PRIMARY DISC.: strictly>50ms gives count=5, not 6 (>=) not 0.5 (fraction)."""
    _reset()
    store = _make_store(
        {
            "atc_disc": [
                (_NOW - float(1000 - 100 * i), float(10 * (i + 1)), True) for i in range(10)
            ],
        }
    )
    result = get_windowed_tool_latency_above_threshold_count(
        "atc_disc", _WIN, 50.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, int)
    assert result == 5, (
        f"strictly>50ms: lats 60,70,80,90,100 -> count=5; kills >=6; kills fraction=0.5; got {result}"
    )


def test_above_threshold_count_exact_boundary_not_counted() -> None:
    """Latency == threshold is NOT counted (strict >)."""
    _reset()
    store = _make_store(
        {
            "atc_exact": [
                (_NOW - 300, 50.0, True),  # == threshold, NOT counted
                (_NOW - 200, 50.0, True),  # == threshold, NOT counted
                (_NOW - 100, 51.0, True),  # > threshold, counted
            ],
        }
    )
    result = get_windowed_tool_latency_above_threshold_count(
        "atc_exact", _WIN, 50.0, store=store, now_ms=_NOW
    )
    assert result == 1, f"only lat=51>50 counted; got {result}"


def test_above_threshold_count_all_above() -> None:
    """All calls above threshold -> count = total n."""
    _reset()
    store = _make_store(
        {
            "atc_all": [(_NOW - float(d), 100.0, True) for d in [300, 200, 100]],
        }
    )
    assert (
        get_windowed_tool_latency_above_threshold_count(
            "atc_all", _WIN, 50.0, store=store, now_ms=_NOW
        )
        == 3
    )


def test_above_threshold_count_none_above() -> None:
    """All calls at or below threshold -> 0."""
    _reset()
    store = _make_store(
        {
            "atc_none": [(_NOW - float(d), 30.0, True) for d in [300, 200, 100]],
        }
    )
    assert (
        get_windowed_tool_latency_above_threshold_count(
            "atc_none", _WIN, 50.0, store=store, now_ms=_NOW
        )
        == 0
    )


def test_above_threshold_count_empty_window_returns_zero() -> None:
    """Empty window -> 0."""
    _reset()
    assert (
        get_windowed_tool_latency_above_threshold_count(
            "no_tool", _WIN, 50.0, store={}, now_ms=_NOW
        )
        == 0
    )


def test_above_threshold_count_outside_window_returns_zero() -> None:
    """All calls outside window -> 0."""
    _reset()
    store = _make_store(
        {
            "atc_old": [(_NOW - _WIN - 100, 100.0, True)] * 5,
        }
    )
    assert (
        get_windowed_tool_latency_above_threshold_count(
            "atc_old", _WIN, 50.0, store=store, now_ms=_NOW
        )
        == 0
    )


def test_returns_int_type() -> None:
    """Return type is int (not float)."""
    _reset()
    store = _make_store(
        {
            "atc_rt": [(_NOW - 100, 100.0, True), (_NOW - 50, 10.0, True)],
        }
    )
    result = get_windowed_tool_latency_above_threshold_count(
        "atc_rt", _WIN, 50.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, int)
    assert result == 1
