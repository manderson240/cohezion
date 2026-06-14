"""Item 1099: get_windowed_fleet_latency_r2_score(window_ms, *, store=None, now_ms=None) -> float
-- fleet OLS R^2 over ALL pooled (timestamp, latency) pairs across tools.
0.0 for <2 pooled calls or zero latency variance.

PRIMARY DISC.: tool_a ts=[t-400,t-200,t-0] lats=[10,20,30]ms (upward trend),
               tool_b ts=[t-400,t-200,t-0] lats=[30,20,10]ms (downward trend)
  pooled 6 points: opposing trends -> slope~=0, R2~=0.0
  (PRIMARY DISC.: kills per-tool-avg-R2: tool_a R2=1.0, tool_b R2=1.0, avg=1.0 != 0;
   pooled opposing trends destroy the linear fit; correct fleet R2~=0.0).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_r2_score,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_r2_primary_discriminator_opposing_trends() -> None:
    """PRIMARY DISC.: pooled R2~0 kills per-tool-avg-R2=1.0.

    tool_a perfect upward: (t-400,10),(t-200,20),(t-0,30) -> R2=1.0
    tool_b perfect downward: (t-400,30),(t-200,20),(t-0,10) -> R2=1.0
    pooled 6 points with same timestamps and opposed slopes: OLS slope=0, R2=0.0.
    """
    _reset()
    store = _make_store(
        {
            "fr2_disc_up": [
                (_NOW - 400, 10.0, True),
                (_NOW - 200, 20.0, True),
                (_NOW - 0, 30.0, True),
            ],
            "fr2_disc_down": [
                (_NOW - 400, 30.0, True),
                (_NOW - 200, 20.0, True),
                (_NOW - 0, 10.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_r2_score(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    # Pooled: 6 equal latency values (10,20,30 from up; 30,20,10 from down).
    # Each timestamp t-400 has lats [10,30], t-200 has [20,20], t-0 has [30,10].
    # OLS slope: relative ts [-400,-400,-200,-200,0,0], lats [10,30,20,20,30,10].
    # t_mean=-200, l_mean=20. Numerator: sum((t-(-200))*(l-20)).
    # Pairs: (-200,10),(-200,30),0,0,(200,30),(200,10) = -200*(-10)+(-200)*10+0+0+200*10+200*(-10)
    #       = 2000-2000+0+0+2000-2000 = 0. So slope=0, intercept=20, SS_res = SS_tot.
    # R2 = 1 - SS_res/SS_tot. SS_tot = var of lats = (10+90+0+0+90+10)/... let's just assert ~0.
    assert abs(result) < 1e-9, (
        f"opposing trends -> fleet R2~0; kills per-tool-avg=1.0; got {result}"
    )


def test_fleet_r2_perfect_single_tool() -> None:
    """Single tool with perfect upward trend -> fleet R2=1.0."""
    _reset()
    store = _make_store(
        {
            "fr2_perf": [
                (_NOW - 600, 10.0, True),
                (_NOW - 400, 20.0, True),
                (_NOW - 200, 30.0, True),
                (_NOW - 0, 40.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_r2_score(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"perfect linear trend -> R2=1.0; got {result}"


def test_fleet_r2_flat_latencies_returns_zero() -> None:
    """All identical latencies -> zero variance in y -> R2=0.0."""
    _reset()
    store = _make_store(
        {
            "fr2_flat_a": [(_NOW - 500, 50.0, True), (_NOW - 300, 50.0, True)],
            "fr2_flat_b": [(_NOW - 200, 50.0, True), (_NOW - 100, 50.0, True)],
        }
    )
    result = get_windowed_fleet_latency_r2_score(_WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"zero variance -> R2=0.0; got {result}"


def test_fleet_r2_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_fleet_latency_r2_score(_WIN, store={}, now_ms=_NOW) == 0.0


def test_fleet_r2_single_pooled_call_returns_zero() -> None:
    """Single pooled call -> <2 -> 0.0."""
    _reset()
    store = _make_store({"fr2_one": [(_NOW - 100, 50.0, True)]})
    assert get_windowed_fleet_latency_r2_score(_WIN, store=store, now_ms=_NOW) == 0.0


def test_fleet_r2_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fr2_old": [(_NOW - _WIN - 100, 10.0, True)] * 5,
        }
    )
    assert get_windowed_fleet_latency_r2_score(_WIN, store=store, now_ms=_NOW) == 0.0


def test_fleet_r2_in_range_zero_to_one() -> None:
    """Fleet R2 always in [0.0, 1.0] for real latency data."""
    _reset()
    store = _make_store(
        {
            "fr2_range_a": [
                (_NOW - 500, 15.0, True),
                (_NOW - 400, 40.0, True),
                (_NOW - 300, 10.0, True),
            ],
            "fr2_range_b": [
                (_NOW - 200, 30.0, True),
                (_NOW - 100, 25.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_r2_score(_WIN, store=store, now_ms=_NOW)
    assert 0.0 <= result <= 1.0, f"R2 must be in [0,1]; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fr2_rt": [(_NOW - float(d), 10.0, True) for d in [300, 200, 100]],
        }
    )
    assert isinstance(get_windowed_fleet_latency_r2_score(_WIN, store=store, now_ms=_NOW), float)
