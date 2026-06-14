"""Item 987: get_windowed_global_error_rate(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide windowed error rate; pools all calls.

PRIMARY DISC.: tool_a 1 error in 1 call + tool_b 0 errors in 3 calls
  -> pooled=1/4=0.25 (NOT per-tool-avg: (1.0+0.0)/2=0.5).
global_success_rate + global_error_rate == 1.0; 0.0 when no recent calls; returns float.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_error_rate,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_error_rate_primary_discriminator() -> None:
    """FALSIFIABLE: tool_a 1/1 error + tool_b 0/3 -> pooled=0.25 (not per-tool-avg=0.5)."""
    _reset()
    store = _make_store(
        {
            "ger_a": [(_NOW - 10, 10.0, False)],  # 1/1 error
            "ger_b": [
                (_NOW - 10, 10.0, True),
                (_NOW - 10, 10.0, True),
                (_NOW - 10, 10.0, True),
            ],  # 0/3
        }
    )
    result = get_windowed_global_error_rate(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 0.25) < 0.001  # 1 error / 4 total calls; not (1.0+0.0)/2=0.5


def test_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_global_error_rate(_WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    store = _make_store(
        {
            "ger_old": [(_NOW - _WIN - 100, 50.0, False)] * 3,
        }
    )
    assert get_windowed_global_error_rate(_WIN, store=store, now_ms=_NOW) == 0.0


def test_all_success_returns_zero() -> None:
    """All tools all successful -> 0.0."""
    store = _make_store(
        {
            "ger_ok1": [(_NOW - 10, 10.0, True)] * 3,
            "ger_ok2": [(_NOW - 10, 20.0, True)] * 2,
        }
    )
    assert abs(get_windowed_global_error_rate(_WIN, store=store, now_ms=_NOW)) < 0.001


def test_all_failure_returns_one() -> None:
    """All failed -> 1.0."""
    store = _make_store(
        {
            "ger_fail1": [(_NOW - 10, 10.0, False)] * 3,
            "ger_fail2": [(_NOW - 10, 20.0, False)] * 2,
        }
    )
    assert abs(get_windowed_global_error_rate(_WIN, store=store, now_ms=_NOW) - 1.0) < 0.001


def test_global_error_plus_success_equals_one() -> None:
    """global_error_rate + global_success_rate == 1.0 for non-empty window."""
    from cohezion.mcp.compound_mcp_telemetry import (
        get_windowed_global_success_count,
        get_windowed_global_error_count,
    )

    store = _make_store(
        {
            "ger_s1": [(_NOW - 10, 10.0, True)] * 3 + [(_NOW - 10, 20.0, False)] * 2,
            "ger_s2": [(_NOW - 10, 30.0, True)] * 4 + [(_NOW - 10, 40.0, False)] * 1,
        }
    )
    er = get_windowed_global_error_rate(_WIN, store=store, now_ms=_NOW)
    # Compute success_rate manually from counts
    ec = get_windowed_global_error_count(_WIN, store=store, now_ms=_NOW)
    sc = get_windowed_global_success_count(_WIN, store=store, now_ms=_NOW)
    sr = float(sc / (ec + sc))
    assert abs(er + sr - 1.0) < 0.001


def test_only_windowed_calls_counted() -> None:
    """Old calls excluded from the rate calculation."""
    store = _make_store(
        {
            "ger_mix": [
                (_NOW - _WIN - 100, 10.0, False),  # old error, excluded
                (_NOW - 10, 20.0, True),
                (_NOW - 10, 30.0, True),
            ]
        }
    )
    result = get_windowed_global_error_rate(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 0.001  # 0 errors in window / 2 calls = 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    store = _make_store(
        {
            "rtype_ger": [(_NOW - 10, 10.0, True)] * 2 + [(_NOW - 10, 20.0, False)] * 1,
        }
    )
    result = get_windowed_global_error_rate(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
