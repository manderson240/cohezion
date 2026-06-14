"""Item 497: largest_improvement() -- class with biggest score decrease (2026-06-08).

``largest_improvement(before, after, weights) -> tuple[str, float] | None``:
Returns (class_name, delta) for the class with the MOST NEGATIVE score delta.
Delta is negative (improvement = score decreased).
None when no class improved.  Tie-break alphabetically.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns (class, NEGATIVE delta) for most-improved class.
     ClassA delta=-5.0 most-improved -> ('ClassA', -5.0) not ('ClassA', 5.0).
     Kills impl returning abs value (delta must be negative).
  2. Returns most-improved (min delta), not most-regressed (max delta).
     ClassA delta=-8.0, ClassB delta=+3.0 -> ('ClassA', -8.0) not ClassB.
     Kills impl reusing largest_regression.
  3. None when no class improved (all stable or worsening).
     Kills impl without no-improvement guard.
  4. Alphabetical tie-break: two classes with same min delta -> alpha-first.
     Kills impl with non-deterministic tie resolution.
  5. Class that disappears entirely from after is improving.
     ClassA in before, absent in after -> delta=-before_score (most-improved candidate).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    largest_improvement,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


WEIGHTS = {"HIGH": 3.0, "LOW": 1.0}


def test_returns_negative_delta_not_abs() -> None:
    """PRIMARY DISC.: delta in returned tuple is negative (score decreased).

    ClassA: 6.0->1.0 = delta -5.0. Result = ('ClassA', -5.0), not ('ClassA', 5.0).
    Kills impl returning abs(delta).
    """
    before = [_p("ClassA", "f1", "HIGH"), _p("ClassA", "f2", "HIGH")]  # 6.0
    after = [_p("ClassA", "f3", "LOW")]  # 1.0
    result = largest_improvement(before, after, WEIGHTS)
    assert isinstance(result, tuple), "Must return tuple; got " + repr(type(result))
    assert result[0] == "ClassA"
    assert abs(result[1] - (-5.0)) < 1e-9, "Delta must be -5.0 (negative); got " + repr(result)


def test_returns_most_improved_not_most_regressed() -> None:
    """Returns most-improved (min delta), not most-regressed (max delta).

    ClassA delta=-8.0 (big improvement), ClassB delta=+3.0 (regression).
    -> ('ClassA', -8.0), not ClassB.
    Kills impl reusing largest_regression.
    """
    before = [
        _p("ClassA", "f1", "HIGH"),
        _p("ClassA", "f2", "HIGH"),
        _p("ClassA", "f3", "HIGH"),  # 9.0
        _p("ClassB", "f4", "LOW"),  # 1.0
    ]
    after = [
        _p("ClassA", "f5", "LOW"),  # 1.0 (delta=-8.0)
        _p("ClassB", "f6", "HIGH"),  # 3.0 (delta=+2.0)
    ]
    result = largest_improvement(before, after, WEIGHTS)
    assert result is not None
    assert result[0] == "ClassA", "ClassA improved most; got " + repr(result)
    assert abs(result[1] - (-8.0)) < 1e-9, "Delta=-8.0; got " + repr(result)


def test_none_when_no_improvement() -> None:
    """None when no class has negative delta (all stable or worsening)."""
    before = [_p("ClassA", "f1", "LOW"), _p("ClassB", "f2", "HIGH")]
    after = [_p("ClassA", "f3", "HIGH"), _p("ClassB", "f4", "HIGH")]
    # ClassA: 1.0->3.0=+2.0; ClassB: 3.0->3.0=0.0
    result = largest_improvement(before, after, WEIGHTS)
    assert result is None, "No negative delta -> None; got " + repr(result)


def test_alphabetical_tie_break() -> None:
    """Two classes with same min delta -> alphabetically first class wins."""
    before = [_p("ClassZ", "f1", "HIGH"), _p("ClassA", "f2", "HIGH")]
    after = [_p("ClassZ", "f3", "LOW"), _p("ClassA", "f4", "LOW")]
    # ClassZ: 3.0->1.0=-2.0; ClassA: 3.0->1.0=-2.0 -> tie; ClassA first
    result = largest_improvement(before, after, WEIGHTS)
    assert result is not None
    assert result[0] == "ClassA", "Tie -> alphabetically first; got " + repr(result)


def test_class_disappearing_fully_is_improving() -> None:
    """Class absent from after has full negative delta."""
    before = [_p("Gone", "f1", "HIGH"), _p("Gone", "f2", "HIGH"), _p("Stay", "f3", "LOW")]
    after = [_p("Stay", "f4", "LOW")]  # Gone absent -> 0.0
    result = largest_improvement(before, after, WEIGHTS)
    assert result is not None
    assert result[0] == "Gone", "Gone (6.0->0.0) is the largest improvement; got " + repr(result)
