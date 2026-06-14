"""Item 491: score_delta_between_snapshots() -- signed score change for a class (2026-06-08).

``score_delta_between_snapshots(before, after, problem_class, weights) -> float``:
Returns class_total_severity_score(after, cls, w) - class_total_severity_score(before, cls, w).
Positive = score increased (worse); negative = score decreased (better).
0.0 when class absent in both.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns SIGNED delta (not abs value).
     after_score=3.0, before_score=7.0 -> delta=-4.0 (not 4.0).
     Kills impl returning absolute value.
  2. Positive delta when after > before (worsening).
     before_score=2.0, after_score=5.0 -> delta=+3.0.
     Kills impl with subtraction reversed (before - after).
  3. Class absent in both -> 0.0 (not raise).
     Kills impl without absence guard.
  4. Class new in after (absent in before) -> full after score as positive delta.
     Kills impl treating absent as raise rather than 0.
  5. Class disappeared from after (absent in after) -> negative delta equal to before score.
     Kills impl treating absent-after as raise rather than 0.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    score_delta_between_snapshots,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


WEIGHTS = {"HIGH": 3.0, "LOW": 1.0}


def test_returns_signed_delta_not_absolute_value() -> None:
    """PRIMARY DISC.: returns signed delta; negative when after < before.

    before ClassA=7.0, after ClassA=3.0 -> delta=-4.0 (not 4.0).
    Kills impl returning abs(delta).
    """
    before = [_p("ClassA", "f1", "HIGH"), _p("ClassA", "f2", "HIGH"), _p("ClassA", "f3", "LOW")]
    after = [_p("ClassA", "f1", "HIGH")]
    result = score_delta_between_snapshots(before, after, "ClassA", WEIGHTS)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert abs(result - (-4.0)) < 1e-9, "delta=3.0-7.0=-4.0; got " + repr(result)


def test_positive_delta_when_score_increases() -> None:
    """Positive delta when after_score > before_score (worsening).

    before ClassA=2.0, after ClassA=5.0 -> delta=+3.0.
    Kills impl with reversed subtraction.
    """
    before = [_p("ClassA", "f1", "LOW")]  # 1.0
    after = [_p("ClassA", "f1", "HIGH"), _p("ClassA", "f2", "HIGH")]  # 6.0
    result = score_delta_between_snapshots(before, after, "ClassA", WEIGHTS)
    assert abs(result - 5.0) < 1e-9, "delta=6.0-1.0=5.0; got " + repr(result)


def test_class_absent_in_both_returns_zero() -> None:
    """Class absent in both before and after -> 0.0 (not raise)."""
    before = [_p("ClassA", "f1", "HIGH")]
    after = [_p("ClassA", "f2", "HIGH")]
    result = score_delta_between_snapshots(before, after, "NONEXISTENT", WEIGHTS)
    assert result == 0.0, "Absent in both -> 0.0; got " + repr(result)


def test_new_class_in_after_gives_positive_delta() -> None:
    """Class appears only in after -> full after score as positive delta."""
    before = [_p("ClassB", "f1", "HIGH")]  # ClassA absent in before
    after = [_p("ClassA", "f2", "HIGH"), _p("ClassB", "f3", "LOW")]
    result = score_delta_between_snapshots(before, after, "ClassA", WEIGHTS)
    assert abs(result - 3.0) < 1e-9, "ClassA new in after: delta=3.0-0.0=3.0; got " + repr(result)


def test_class_disappeared_from_after_gives_negative_delta() -> None:
    """Class only in before (absent after) -> negative delta equal to before score."""
    before = [_p("ClassA", "f1", "HIGH"), _p("ClassA", "f2", "HIGH")]  # 6.0
    after = [_p("ClassB", "f3", "LOW")]  # ClassA absent
    result = score_delta_between_snapshots(before, after, "ClassA", WEIGHTS)
    assert abs(result - (-6.0)) < 1e-9, "ClassA gone: delta=0.0-6.0=-6.0; got " + repr(result)
