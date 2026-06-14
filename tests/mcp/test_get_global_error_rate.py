"""Item 945: get_global_error_rate() -> float -- overall error rate.

PRIMARY DISC.: tool A has 6 calls, 0 errors (rate=0.0);
tool B has 2 calls, 2 errors (rate=1.0);
naive avg-of-rates = (0.0+1.0)/2 = 0.5 WRONG;
correct = 2 errors / 8 calls = 0.25.
Kills impl averaging per-tool rates.
empty -> 0.0; returns float.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_global_error_rate,
)


def _reset():
    clear_telemetry_stores()


def test_weighted_not_naive_average_primary_discriminator() -> None:
    """FALSIFIABLE: tool A=6 calls 0 errors, tool B=2 calls 2 errors.
    naive_avg=(0+1)/2=0.5 WRONG. correct=2/8=0.25.
    Kills impl averaging per-tool error rates."""
    _reset()
    for _ in range(6):
        record_tool_call("high_volume", 5.0, True)  # 0 errors
    for _ in range(2):
        record_tool_call("all_errors", 5.0, False)  # 2 errors
    result = get_global_error_rate()
    # Correct: 2 / 8 = 0.25
    assert abs(result - 0.25) < 0.001
    # Discriminate naive average (0.5)
    assert abs(result - 0.5) > 0.1


def test_empty_store_returns_zero() -> None:
    """No calls -> 0.0."""
    _reset()
    assert get_global_error_rate() == 0.0


def test_returns_float() -> None:
    """Return type is float."""
    _reset()
    record_tool_call("float_ger", 5.0, True)
    assert isinstance(get_global_error_rate(), float)


def test_all_success_returns_zero() -> None:
    """All calls succeed -> 0.0."""
    _reset()
    for _ in range(5):
        record_tool_call("clean_ger", 5.0, True)
    assert get_global_error_rate() == 0.0


def test_all_errors_returns_one() -> None:
    """All calls fail -> 1.0."""
    _reset()
    for _ in range(4):
        record_tool_call("all_fail_ger", 5.0, False)
    assert abs(get_global_error_rate() - 1.0) < 0.001


def test_consistent_with_total_counts() -> None:
    """global_error_rate == total_error_count / total_call_count."""
    from cohezion.mcp.compound_mcp_telemetry import (
        get_total_error_count,
        get_total_call_count,
    )

    _reset()
    record_tool_call("cons_a", 5.0, True)
    record_tool_call("cons_a", 5.0, False)
    record_tool_call("cons_b", 5.0, True)
    record_tool_call("cons_b", 5.0, True)
    record_tool_call("cons_b", 5.0, False)
    result = get_global_error_rate()
    expected = get_total_error_count() / get_total_call_count()
    assert abs(result - expected) < 0.001
