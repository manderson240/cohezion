"""Item 1077: get_windowed_tool_latency_ewma_ms(tool_name, window_ms, alpha, *, store=None, now_ms=None) -> float
-- per-tool EWMA latency (ordered by timestamp, oldest-to-newest).

alpha = smoothing factor (0 < alpha <= 1).
alpha=1.0 returns the most recent latency.
0.0 for empty window.
Injectable store. Pure function.

PRIMARY DISC.: lats [10,50,20] in timestamp order (t1<t2<t3), alpha=0.5
  v0=10 (seed with oldest)
  v1=0.5*50+0.5*10=30.0
  v2=0.5*20+0.5*30=25.0
  EWMA=25.0
  (PRIMARY DISC.: kills simple mean=(10+50+20)/3=26.67 (uniform weighting ignores recency);
   kills last-value=20 (only correct for alpha=1);
   correct EWMA(alpha=0.5)=25.0).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_ewma_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_ewma_primary_discriminator() -> None:
    """PRIMARY DISC.: [10,50,20] ordered oldest->newest, alpha=0.5 -> EWMA=25.0.

    Kills simple mean=26.67 (ignores recency).
    Kills last-value=20 (alpha=1 only).
    Correct: EWMA(0.5)=25.0.
    """
    _reset()
    store = _make_store({
        "ewma_disc": [
            (_NOW - 300, 10.0, True),  # oldest
            (_NOW - 200, 50.0, True),
            (_NOW - 100, 20.0, True),  # newest
        ],
    })
    result = get_windowed_tool_latency_ewma_ms("ewma_disc", _WIN, 0.5, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 25.0) < 1e-9, (
        f"EWMA(0.5)=25.0; kills mean=26.67; kills last=20; got {result}"
    )


def test_ewma_alpha_one_returns_most_recent() -> None:
    """alpha=1.0 -> EWMA collapses to the most recent (youngest) value."""
    _reset()
    store = _make_store({
        "ewma_a1": [
            (_NOW - 300, 10.0, True),
            (_NOW - 200, 50.0, True),
            (_NOW - 100, 20.0, True),
        ],
    })
    result = get_windowed_tool_latency_ewma_ms("ewma_a1", _WIN, 1.0, store=store, now_ms=_NOW)
    assert abs(result - 20.0) < 1e-9, f"alpha=1 -> most recent=20.0; got {result}"


def test_ewma_single_sample_returns_that_value() -> None:
    """Single sample -> EWMA = that value regardless of alpha."""
    _reset()
    store = _make_store({
        "ewma_single": [(_NOW - 100, 42.0, True)],
    })
    result = get_windowed_tool_latency_ewma_ms("ewma_single", _WIN, 0.3, store=store, now_ms=_NOW)
    assert abs(result - 42.0) < 1e-9, f"single sample -> EWMA=42.0; got {result}"


def test_ewma_empty_window_returns_zero() -> None:
    """Empty window -> 0.0."""
    _reset()
    assert get_windowed_tool_latency_ewma_ms("no_tool", _WIN, 0.5, store={}, now_ms=_NOW) == 0.0


def test_ewma_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "ewma_old": [(_NOW - _WIN - 100, 50.0, True)] * 3,
    })
    assert get_windowed_tool_latency_ewma_ms("ewma_old", _WIN, 0.5, store=store, now_ms=_NOW) == 0.0


def test_ewma_recency_weighting_direction() -> None:
    """Confirms EWMA weights newer values MORE (alpha>0.5 gives higher weight to recent).

    [100, 10] newest=10, alpha=0.9 -> v0=100; v1=0.9*10+0.1*100=9+10=19.0.
    Mean=55.0. EWMA < mean confirms recency weighting toward the low recent value.
    """
    _reset()
    store = _make_store({
        "ewma_dir": [
            (_NOW - 200, 100.0, True),  # old, high latency
            (_NOW - 100, 10.0, True),   # recent, low latency
        ],
    })
    result = get_windowed_tool_latency_ewma_ms("ewma_dir", _WIN, 0.9, store=store, now_ms=_NOW)
    assert abs(result - 19.0) < 1e-9, f"EWMA(0.9)=[100,10]=19.0; got {result}"
    assert result < 55.0, f"EWMA must be less than mean=55 (recency weighted); got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"ewma_rt": [(_NOW - 10, 50.0, True)] * 3})
    assert isinstance(get_windowed_tool_latency_ewma_ms("ewma_rt", _WIN, 0.5, store=store, now_ms=_NOW), float)
