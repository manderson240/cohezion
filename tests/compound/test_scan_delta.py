"""Item 225: scan_delta() — diff two scan summaries (2026-06-08).

``scan_delta(before: dict, after: dict)``
-> ``dict``:
Diffs two ``summarize_scan()`` result dicts, returning a change summary with
5 keys:
  - ``new_violations``:  int  — violations_count gained (after - before)
  - ``resolved_violations``: int — violations_count lost (before - after, ≥0)
  - ``total_delta``:     int  — change in total finding count
  - ``newly_over``:      frozenset[str] — classes that crossed into over-threshold
  - ``newly_under``:     frozenset[str] — classes that moved back under threshold

Identical inputs → all-zero/empty delta.  Pure; no I/O.

Use to detect regressions between two consecutive scans::

    before = summarize_scan(prev_problems, limits)
    after  = summarize_scan(curr_problems, limits)
    delta  = scan_delta(before, after)
    if delta["new_violations"] > 0:
        alert(delta["newly_over"])

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: newly_over = after["classes_over"] - before["classes_over"]
     (SET DIFFERENCE, not just after["classes_over"]).
     Kills an impl that returns after["classes_over"] unchanged.
  2. resolved_violations = violations_count reduction (non-negative, clamped or
     computed correctly).
     Kills an impl that returns negative values when violations drop.
  3. Identical before/after -> all-zero/empty delta.
     Kills an impl that returns after["classes_over"] as newly_over when no
     change occurred.
  4. total_delta = after["total"] - before["total"] (may be negative).
     Kills an impl that takes abs() or clamps to 0.
  5. newly_under = before["classes_over"] - after["classes_over"]
     (classes that left the over-threshold set).
     Kills an impl that returns after["classes_under"] as newly_under.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    scan_delta,
    summarize_scan,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


def _summary(problems, thresholds):
    return summarize_scan(problems, thresholds)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_newly_over_is_set_difference_not_after_classes_over() -> None:
    """newly_over = after["classes_over"] - before["classes_over"].

    PRIMARY DISCRIMINATOR: kills an impl returning after["classes_over"] whole.
    Before: alpha is under threshold.  After: alpha crosses over.
    newly_over must be {"alpha"}, not {"alpha", ...everything in after}.
    """
    thresholds = {"alpha": 2, "beta": 10}
    before = _summary([_p("alpha", 0), _p("beta", 0)], thresholds)  # alpha under, beta under
    after = _summary(
        [_p("alpha", i) for i in range(4)] + [_p("beta", 0)], thresholds
    )  # alpha over, beta still under

    delta = scan_delta(before, after)

    assert delta["newly_over"] == frozenset({"alpha"}), (
        "newly_over must be {'alpha'} (alpha crossed over); got " + repr(delta["newly_over"])
    )


def test_resolved_violations_non_negative_when_violations_drop() -> None:
    """resolved_violations ≥ 0; equals violations_count drop.

    Kills an impl that returns a raw subtraction (can go negative).
    Before: alpha violating (violations_count=1).
    After: alpha compliant (violations_count=0).
    resolved_violations must be 1.
    """
    thresholds = {"alpha": 2}
    before = _summary([_p("alpha", i) for i in range(5)], thresholds)  # alpha: 5>2, violating
    after = _summary([_p("alpha", 0)], thresholds)  # alpha: 1<=2, compliant

    delta = scan_delta(before, after)

    assert delta["resolved_violations"] == 1, (
        "resolved_violations must be 1 (violation dropped); got "
        + repr(delta["resolved_violations"])
    )
    assert delta["new_violations"] == 0, "new_violations must be 0; got " + repr(
        delta["new_violations"]
    )


def test_identical_inputs_gives_zero_delta() -> None:
    """Identical before/after -> all-zero/empty delta.

    Kills an impl that reports newly_over=after["classes_over"] on no-change.
    """
    problems = [_p("alpha", i) for i in range(3)] + [_p("beta", 0)]
    thresholds = {"alpha": 2, "beta": 5}
    snap = _summary(problems, thresholds)

    delta = scan_delta(snap, snap)

    assert delta["new_violations"] == 0, "no change -> new_violations=0; got " + repr(delta)
    assert delta["resolved_violations"] == 0, "no change -> resolved=0; got " + repr(delta)
    assert delta["total_delta"] == 0, "no change -> total_delta=0; got " + repr(delta)
    assert delta["newly_over"] == frozenset(), "no change -> newly_over=frozenset(); got " + repr(
        delta
    )
    assert delta["newly_under"] == frozenset(), "no change -> newly_under=frozenset(); got " + repr(
        delta
    )


def test_total_delta_can_be_negative() -> None:
    """total_delta = after["total"] - before["total"], may be negative.

    Kills an impl that takes abs() or clamps to 0.
    Before: 5 findings. After: 2 findings. total_delta = -3.
    """
    thresholds = {"alpha": 10}
    before = _summary([_p("alpha", i) for i in range(5)], thresholds)
    after = _summary([_p("alpha", i) for i in range(2)], thresholds)

    delta = scan_delta(before, after)

    assert delta["total_delta"] == -3, "total_delta must be -3; got " + repr(delta["total_delta"])


def test_newly_under_is_classes_that_left_over_set() -> None:
    """newly_under = before["classes_over"] - after["classes_over"].

    Kills an impl that returns after["classes_under"] (which is a different set).
    Before: alpha violating. After: alpha compliant. newly_under = {"alpha"}.
    """
    thresholds = {"alpha": 2, "beta": 5}
    before = _summary(
        [_p("alpha", i) for i in range(4)] + [_p("beta", 0)], thresholds
    )  # alpha over
    after = _summary([_p("alpha", 0), _p("beta", 0)], thresholds)  # alpha now under

    delta = scan_delta(before, after)

    assert delta["newly_under"] == frozenset({"alpha"}), (
        "newly_under must be {'alpha'} (alpha moved back under); got " + repr(delta["newly_under"])
    )
