"""Behavior tests for the Claude usage monitor (task #15, 2026-06-07).

User directive: "We need a way to monitor our claude usage so we don't hit our limits too
soon." `summarize_usage` aggregates per-message token usage (parsed from the Claude Code
transcript JSONL) into time windows so the user — and the loops — can see burn rate and back
off before the cap.

Discriminating: window filtering by timestamp. An impl that sums ALL records regardless of
the window (the most plausible wrong version) fails test_window_excludes_old_records — the
"hour" window must contain only records inside it, and burn rate must scale to the window.
"""

from __future__ import annotations

from cohezion.observability.claude_usage import (
    UsageRecord,
    summarize_usage,
    usage_guard,
)


_HOUR = 3600.0
_DAY = 86400.0


def _summary_with_total(total_tokens: int) -> dict:
    # one record whose output drives the window total to `total_tokens` (input=0).
    rec = UsageRecord(ts=1_000_000.0, input=0, output=total_tokens, cache_read=0, cache_creation=0)
    return summarize_usage([rec], now_ts=1_000_000.0, windows={"week": 7 * _DAY})


def test_usage_guard_proceeds_below_soft() -> None:
    s = _summary_with_total(100)
    assert usage_guard(s, window="week", soft_budget=1000, hard_budget=2000) == "proceed"


def test_usage_guard_throttles_between_soft_and_hard() -> None:
    s = _summary_with_total(1500)
    assert usage_guard(s, window="week", soft_budget=1000, hard_budget=2000) == "throttle"


def test_usage_guard_halts_at_or_above_hard() -> None:
    s = _summary_with_total(2000)
    assert usage_guard(s, window="week", soft_budget=1000, hard_budget=2000) == "halt"


def test_usage_guard_off_when_no_budget() -> None:
    # No budget configured → never throttle (gate off), even at huge spend.
    s = _summary_with_total(10**12)
    assert usage_guard(s, window="week", soft_budget=0, hard_budget=0) == "proceed"


def _rec(ts: float, out: int) -> UsageRecord:
    return UsageRecord(ts=ts, input=1, output=out, cache_read=0, cache_creation=0)


def test_window_excludes_old_records() -> None:
    now = 1_000_000.0
    records = [
        _rec(now - 30 * 60, 100),  # 30 min ago — inside the hour
        _rec(now - 90 * 60, 200),  # 90 min ago — OUTSIDE the hour, inside the day
        _rec(now - 5 * _DAY, 400),  # 5 days ago — outside both
    ]
    summary = summarize_usage(records, now_ts=now, windows={"hour": _HOUR, "day": _DAY})

    # hour window: ONLY the 30-min record (an all-records impl would report 700 output)
    assert summary["hour"].output == 100
    assert summary["hour"].records == 1
    # day window: the 30-min AND 90-min records, not the 5-day one
    assert summary["day"].output == 300
    assert summary["day"].records == 2


def test_total_and_burn_rate() -> None:
    now = 1_000_000.0
    # two records inside the hour, 600 output total
    records = [_rec(now - 10 * 60, 250), _rec(now - 50 * 60, 350)]
    summary = summarize_usage(records, now_ts=now, windows={"hour": _HOUR})
    w = summary["hour"]
    assert w.total == 600 + 2  # output 600 + input 1*2 (+0 cache)
    # burn = total tokens / hours elapsed in the window (1.0h) → equals total
    assert abs(w.burn_per_hour - float(w.total)) < 1e-6


def test_empty_window_is_zero_not_error() -> None:
    summary = summarize_usage([], now_ts=1_000_000.0, windows={"hour": _HOUR})
    assert summary["hour"].total == 0
    assert summary["hour"].records == 0
    assert summary["hour"].burn_per_hour == 0.0
