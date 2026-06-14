"""Item 1068: get_windowed_tool_latency_interquartile_range_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- per-tool IQR = Q3 - Q1 (p75 - p25).

0.0 for empty window. Thin composition via get_windowed_latency_percentile.
Injectable store. Pure function.

PRIMARY DISC.: lats [10,20,30,40,50] n=5
  Q1=idx=0.25*4=1.0 -> 20.0 (exact)
  Q3=idx=0.75*4=3.0 -> 40.0 (exact)
  IQR = 40.0 - 20.0 = 20.0
  (PRIMARY DISC.: kills range=max-min=50-10=40 (different statistic);
   kills half-IQR=10 (variant, not IQR);
   correct IQR=Q3-Q1=40-20=20.0).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_interquartile_range_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_iqr_primary_discriminator() -> None:
    """PRIMARY DISC.: [10,20,30,40,50] -> IQR=Q3-Q1=40-20=20.0.

    Kills range=40 (max-min, different statistic).
    Kills half-IQR=10 (variant).
    Correct: IQR=20.0.
    """
    _reset()
    store = _make_store(
        {
            "iqr_disc": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
        }
    )
    result = get_windowed_tool_latency_interquartile_range_ms(
        "iqr_disc", _WIN, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert abs(result - 20.0) < 1e-9, (
        f"IQR=Q3-Q1=40-20=20.0; kills range=40; kills half-IQR=10; got {result}"
    )


def test_iqr_uniform_distribution_returns_nonzero() -> None:
    """[10,20,30,40,50,60,70,80,90,100] n=10 -> Q1=idx=2.25->27.5; Q3=idx=6.75->72.5; IQR=45.0."""
    _reset()
    store = _make_store(
        {
            "iqr_uni": [(_NOW - 10, float(v), True) for v in range(10, 101, 10)],
        }
    )
    result = get_windowed_tool_latency_interquartile_range_ms(
        "iqr_uni", _WIN, store=store, now_ms=_NOW
    )
    # Q1: idx=0.25*9=2.25 -> sorted[2]+0.25*(sorted[3]-sorted[2])=30+0.25*10=32.5?
    # Wait: [10,20,30,40,50,60,70,80,90,100]
    # Q1: idx=0.25*9=2.25 -> sorted[2]+0.25*(sorted[3]-sorted[2])=30+0.25*(40-30)=32.5
    # Q3: idx=0.75*9=6.75 -> sorted[6]+0.75*(sorted[7]-sorted[6])=70+0.75*(80-70)=77.5
    # IQR=77.5-32.5=45.0
    assert abs(result - 45.0) < 1e-9, f"uniform [10..100] -> IQR=45.0; got {result}"


def test_iqr_all_equal_returns_zero() -> None:
    """All equal -> Q1=Q3=constant -> IQR=0.0."""
    _reset()
    store = _make_store(
        {
            "iqr_eq": [(_NOW - 10, 50.0, True)] * 6,
        }
    )
    result = get_windowed_tool_latency_interquartile_range_ms(
        "iqr_eq", _WIN, store=store, now_ms=_NOW
    )
    assert abs(result - 0.0) < 1e-9, f"all-equal -> IQR=0.0; got {result}"


def test_iqr_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert (
        get_windowed_tool_latency_interquartile_range_ms("no_such_iqr", _WIN, store={}, now_ms=_NOW)
        == 0.0
    )


def test_iqr_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "iqr_old": [(_NOW - _WIN - 100, float(v), True) for v in [10, 20, 30, 40, 50]],
        }
    )
    assert (
        get_windowed_tool_latency_interquartile_range_ms("iqr_old", _WIN, store=store, now_ms=_NOW)
        == 0.0
    )


def test_iqr_non_negative() -> None:
    """IQR >= 0 always (Q3 >= Q1 for sorted data)."""
    _reset()
    store = _make_store(
        {
            "iqr_pos": [(_NOW - 10, float(v), True) for v in [5, 10, 15, 100, 500]],
        }
    )
    result = get_windowed_tool_latency_interquartile_range_ms(
        "iqr_pos", _WIN, store=store, now_ms=_NOW
    )
    assert result >= 0.0, f"IQR must be non-negative; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"iqr_rt": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]]})
    assert isinstance(
        get_windowed_tool_latency_interquartile_range_ms("iqr_rt", _WIN, store=store, now_ms=_NOW),
        float,
    )
