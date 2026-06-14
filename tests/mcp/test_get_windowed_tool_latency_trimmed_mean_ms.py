"""Item 1034: get_windowed_tool_latency_trimmed_mean_ms(tool_name, window_ms, trim_pct=0.1, *, store=None, now_ms=None) -> float
-- trimmed (truncated) mean of latency in window.

Discard floor(trim_pct * n) values from EACH tail, compute mean of remaining.
0.0 for unknown/empty tool, or if nothing remains after trimming.
Injectable store. Pure function. Default trim_pct=0.1 (10% each tail).

PRIMARY DISC.: lats [10, 20, 30, 40, 100] trim_pct=0.2
  n=5, k=floor(0.2*5)=1 -> discard 1 from each end
  sorted=[10,20,30,40,100] -> keep [20,30,40] -> trimmed_mean=90/3=30.0
  (PRIMARY DISC.: kills full_mean=40.0; kills median=30.0 (same value but wrong algorithm);
   kills k=0 (no trimming) which gives 40.0; correct trimmed_mean=30.0 float).

Note: When trim_pct=0.2, full_mean=40 vs trimmed_mean=30 - the discriminating value
HAPPENS to equal the median here, but the algorithm is different (floor-trim not sort-select).
The test also verifies trim_pct=0 gives full_mean to confirm trim amount matters.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_trimmed_mean_ms,
    get_windowed_tool_mean_latency_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_trimmed_mean_primary_discriminator() -> None:
    """PRIMARY DISC.: [10,20,30,40,100] trim_pct=0.2 -> trimmed_mean=30.0.

    Kills full_mean=40.0 (no trimming removes the outlier 100).
    Kills k=0 (trim of zero gives 40.0 not 30.0).
    Correct: trim 1 from each end, mean([20,30,40])=30.0.
    """
    _reset()
    store = _make_store(
        {
            "tm_a": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 100]],
        }
    )
    result = get_windowed_tool_latency_trimmed_mean_ms("tm_a", _WIN, 0.2, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 30.0) < 1e-9, f"trimmed_mean=30.0; kills full_mean=40.0; got {result}"


def test_trim_zero_equals_full_mean() -> None:
    """trim_pct=0.0 -> trimmed mean == full mean (no data discarded)."""
    _reset()
    lats = [10.0, 50.0, 200.0, 300.0]
    store = _make_store(
        {
            "tm_zero": [(_NOW - 10, v, True) for v in lats],
        }
    )
    trimmed = get_windowed_tool_latency_trimmed_mean_ms(
        "tm_zero", _WIN, 0.0, store=store, now_ms=_NOW
    )
    full = get_windowed_tool_mean_latency_ms("tm_zero", _WIN, store=store, now_ms=_NOW)
    assert abs(trimmed - full) < 1e-9, f"trim=0: trimmed={trimmed} must equal full={full}"


def test_trim_removes_outlier() -> None:
    """Trimming reduces the outlier's influence on the mean."""
    _reset()
    # Without trim: mean=(10*9+10000)/10 = 1009
    # With trim 10% (k=1): mean of [10]*8 / 8 = 10
    lats = [10.0] * 9 + [10000.0]
    store = _make_store(
        {
            "tm_out": [(_NOW - 10, v, True) for v in lats],
        }
    )
    trimmed = get_windowed_tool_latency_trimmed_mean_ms(
        "tm_out", _WIN, 0.1, store=store, now_ms=_NOW
    )
    full = get_windowed_tool_mean_latency_ms("tm_out", _WIN, store=store, now_ms=_NOW)
    assert trimmed < full, f"trimmed={trimmed} must be < full_mean={full} (outlier removed)"
    assert abs(trimmed - 10.0) < 1e-9, f"trimmed mean of [10]*8 = 10.0; got {trimmed}"


def test_all_equal_trimmed_equals_value() -> None:
    """All equal -> trimmed mean == that value."""
    _reset()
    store = _make_store(
        {
            "tm_eq": [(_NOW - 10, 100.0, True)] * 10,
        }
    )
    result = get_windowed_tool_latency_trimmed_mean_ms("tm_eq", _WIN, 0.1, store=store, now_ms=_NOW)
    assert abs(result - 100.0) < 1e-9, f"all-equal -> trimmed_mean=100.0; got {result}"


def test_default_trim_pct_is_0_1() -> None:
    """Default trim_pct is 0.1 (10% each tail)."""
    _reset()
    lats = [1.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 100.0]  # n=10
    store = _make_store(
        {
            "tm_def": [(_NOW - 10, v, True) for v in lats],
        }
    )
    default = get_windowed_tool_latency_trimmed_mean_ms("tm_def", _WIN, store=store, now_ms=_NOW)
    explicit = get_windowed_tool_latency_trimmed_mean_ms(
        "tm_def", _WIN, 0.1, store=store, now_ms=_NOW
    )
    assert abs(default - explicit) < 1e-9, f"default==0.1: {default} vs {explicit}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert (
        get_windowed_tool_latency_trimmed_mean_ms("no_such_tm", _WIN, store={}, now_ms=_NOW) == 0.0
    )


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "tm_old": [(_NOW - _WIN - 100, 100.0, True)] * 5,
        }
    )
    assert (
        get_windowed_tool_latency_trimmed_mean_ms("tm_old", _WIN, store=store, now_ms=_NOW) == 0.0
    )


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"tm_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 200]]})
    assert isinstance(
        get_windowed_tool_latency_trimmed_mean_ms("tm_rt", _WIN, store=store, now_ms=_NOW), float
    )
