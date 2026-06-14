"""Item 926: record_tool_call_all_windowed — alias for record_tool_call_all.

PRIMARY DISC.: after one call, BOTH cumulative and windowed stores populated.
Kills impl that only writes to one store.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    clear_telemetry_stores,
    get_tool_call_count,
    get_tool_windowed_call_count,
    record_tool_call_all_windowed,
)


NOW = 60_000.0


def _reset():
    clear_telemetry_stores()


def test_both_stores_populated_primary_discriminator() -> None:
    """FALSIFIABLE: after one call -> cumulative count > 0 AND windowed count > 0.
    Kills impl writing to only one store."""
    _reset()
    record_tool_call_all_windowed("dual_tool", 25.0, True, ts_ms=NOW - 100)
    # cumulative store
    assert get_tool_call_count("dual_tool") == 1
    # windowed store (with a 5s window)
    assert (
        get_tool_windowed_call_count(
            "dual_tool", window_ms=5000.0, store=_WINDOWED_TELEMETRY, now_ms=NOW
        )
        == 1
    )


def test_same_latency_in_both_stores() -> None:
    """The recorded latency must match in both stores."""
    _reset()
    record_tool_call_all_windowed("match_tool", 77.0, True, ts_ms=NOW - 50)
    from cohezion.mcp.compound_mcp_telemetry import get_tool_p50_ms, get_tool_windowed_p95_ms

    assert abs(get_tool_p50_ms("match_tool") - 77.0) < 0.01
    assert (
        abs(
            get_tool_windowed_p95_ms(
                "match_tool", window_ms=5000.0, store=_WINDOWED_TELEMETRY, now_ms=NOW
            )
            - 77.0
        )
        < 0.01
    )


def test_failed_call_increments_both_stores() -> None:
    _reset()
    record_tool_call_all_windowed("fail_tool", 10.0, False, ts_ms=NOW - 100)
    from cohezion.mcp.compound_mcp_telemetry import (
        get_tool_error_rate,
        get_tool_windowed_error_rate,
    )

    assert abs(get_tool_error_rate("fail_tool") - 1.0) < 0.001
    assert (
        abs(
            get_tool_windowed_error_rate(
                "fail_tool", window_ms=5000.0, store=_WINDOWED_TELEMETRY, now_ms=NOW
            )
            - 1.0
        )
        < 0.001
    )


def test_multiple_calls_count_consistently() -> None:
    _reset()
    for i in range(3):
        record_tool_call_all_windowed(
            "multi_tool", float(10 * (i + 1)), True, ts_ms=NOW - (i + 1) * 100
        )
    assert get_tool_call_count("multi_tool") == 3
    assert (
        get_tool_windowed_call_count(
            "multi_tool", window_ms=5000.0, store=_WINDOWED_TELEMETRY, now_ms=NOW
        )
        == 3
    )


def test_ts_ms_defaults_to_now() -> None:
    """ts_ms=None should use current time — call should appear in a recent window."""
    _reset()
    import time

    record_tool_call_all_windowed("now_tool", 5.0, True)  # ts_ms defaults to now
    now = time.time() * 1000.0
    count = get_tool_windowed_call_count(
        "now_tool", window_ms=5000.0, store=_WINDOWED_TELEMETRY, now_ms=now
    )
    assert count == 1
