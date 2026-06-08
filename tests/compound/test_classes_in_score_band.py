"""Item 508: classes_in_score_band() -- classes whose total score is in [lo, hi] (2026-06-08).

``classes_in_score_band(problems, weights, lo, hi) -> frozenset[str]``:
Returns frozenset of class names whose total weighted severity score is within
the INCLUSIVE range [lo, hi].  lo > hi -> frozenset() (empty by contract).
Empty problems -> frozenset().  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns frozenset of CLASS NAMES (not Problem objects).
     Kills impl filtering Problem records directly instead of class totals.
  2. Inclusive on BOTH ends: lo <= score <= hi.
     Kills impl using strict inequality (lo < score < hi).
  3. lo > hi -> frozenset() by contract (not raise).
     Kills impl raising ValueError or returning all classes.
  4. Class exactly at lo or exactly at hi is INCLUDED.
     Discriminates the inclusion boundary (complements the strict tests).
  5. Empty problems -> frozenset() (not raise).
     Kills impl without empty guard.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    classes_in_score_band,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_frozenset_of_class_names() -> None:
    """PRIMARY DISC.: returns frozenset of class names, not Problem objects.

    Kills impl that filters Problem records rather than computing class totals.
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),   # score 5.0
        _p("ClassB", "f2", "MED"),    # score 3.0
        _p("ClassC", "f3", "LOW"),    # score 1.0
    ]
    weights = {"HIGH": 5.0, "MED": 3.0, "LOW": 1.0}
    result = classes_in_score_band(problems, weights, lo=2.0, hi=4.0)
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))
    assert all(isinstance(x, str) for x in result), "Items must be str; got " + repr(result)
    assert result == frozenset({"ClassB"}), (
        "Only ClassB (3.0) in [2.0, 4.0]; got " + repr(result)
    )


def test_inclusive_on_both_ends() -> None:
    """Band is INCLUSIVE: lo <= score AND score <= hi.

    ClassA=5.0, ClassB=3.0, ClassC=1.0; band [3.0, 5.0] includes both A and B.
    Kills impl using strict inequalities (would exclude the endpoints).
    """
    problems = [
        _p("A", "f1", "HIGH"),   # 5.0
        _p("B", "f2", "MED"),    # 3.0
        _p("C", "f3", "LOW"),    # 1.0
    ]
    result = classes_in_score_band(problems, {"HIGH": 5.0, "MED": 3.0, "LOW": 1.0}, 3.0, 5.0)
    assert "A" in result, "A at 5.0 (== hi) must be included; got " + repr(result)
    assert "B" in result, "B at 3.0 (== lo) must be included; got " + repr(result)
    assert "C" not in result, "C at 1.0 is below lo=3.0; got " + repr(result)


def test_lo_greater_than_hi_returns_empty() -> None:
    """lo > hi -> frozenset() (not raise, not all classes).

    Kills impl raising ValueError or using abs(hi-lo).
    """
    problems = [_p("A", "f1", "HIGH")]
    result = classes_in_score_band(problems, {"HIGH": 5.0}, lo=10.0, hi=5.0)
    assert result == frozenset(), "lo > hi -> frozenset(); got " + repr(result)


def test_class_exactly_at_boundary_included() -> None:
    """Class with score exactly at lo OR exactly at hi is included.

    lo=3.0, hi=7.0: ClassA=3.0 (at lo), ClassB=7.0 (at hi), ClassC=5.0 (inside).
    All three are within the inclusive band.
    Kills impl with off-by-one on boundary exclusion.
    """
    problems = [
        _p("A", "f1", "LOW"),    # 3.0 = lo
        _p("B", "f2", "HIGH"),   # 7.0 = hi
        _p("C", "f3", "MED"),    # 5.0 inside
    ]
    result = classes_in_score_band(
        problems, {"LOW": 3.0, "MED": 5.0, "HIGH": 7.0}, lo=3.0, hi=7.0
    )
    assert result == frozenset({"A", "B", "C"}), (
        "All three in band; got " + repr(result)
    )


def test_empty_problems_returns_empty_frozenset() -> None:
    """Empty problems -> frozenset() (not raise)."""
    result = classes_in_score_band([], {"HIGH": 3.0}, lo=0.0, hi=10.0)
    assert result == frozenset(), "Empty -> frozenset(); got " + repr(result)
