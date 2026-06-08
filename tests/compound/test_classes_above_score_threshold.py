"""Item 489: classes_above_score_threshold() -- class names with score > threshold (2026-06-08).

``classes_above_score_threshold(problems, weights, threshold) -> frozenset[str]``:
Returns frozenset of class names whose total weighted severity score STRICTLY
exceeds *threshold*.  Classes at exactly threshold are excluded.
Empty problems -> frozenset().  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns classes ABOVE (not below) threshold.
     ClassA score=7.0, ClassB score=3.0; threshold=5.0 -> {'ClassA'}.
     Kills impl returning the complement (under-threshold set).
  2. STRICT inequality: class at exactly threshold is excluded.
     ClassA score=5.0, threshold=5.0 -> frozenset().
     Kills impl using >= (>= threshold includes at-boundary cases).
  3. Return type is frozenset (not set, not list).
     Kills impl returning a plain set or list.
  4. Empty problems -> frozenset() (not raise).
     Kills impl without empty-input guard.
  5. Unknown severity contributes 0 -- class may stay below threshold.
     ClassA has only UNKNOWN_SEV; threshold=0.5 -> frozenset().
     Kills impl that crashes on missing weight keys.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    classes_above_score_threshold,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_classes_above_not_below_threshold() -> None:
    """PRIMARY DISC.: returns classes whose score EXCEEDS threshold.

    ClassA: 2xHIGH + 1xLOW = 7.0; ClassB: 1xHIGH = 3.0; threshold=5.0.
    -> frozenset({'ClassA'}).
    Kills impl returning the complement (under-threshold set).
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),
        _p("ClassA", "f2", "HIGH"),
        _p("ClassA", "f3", "LOW"),
        _p("ClassB", "f4", "HIGH"),
    ]
    weights = {"HIGH": 3.0, "LOW": 1.0}
    result = classes_above_score_threshold(problems, weights, 5.0)
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))
    assert result == frozenset({"ClassA"}), (
        "Only ClassA (7.0) > 5.0; got " + repr(result)
    )


def test_strict_inequality_excludes_exact_threshold() -> None:
    """Class at exactly threshold is NOT included (strict >).

    ClassA score=5.0, threshold=5.0 -> frozenset() (not included).
    Kills impl using >= instead of >.
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),
        _p("ClassA", "f2", "LOW"),  # 3.0 + 2.0 = 5.0 exactly
    ]
    weights = {"HIGH": 3.0, "LOW": 2.0}
    result = classes_above_score_threshold(problems, weights, 5.0)
    assert result == frozenset(), (
        "Score==threshold -> excluded (strict >); got " + repr(result)
    )


def test_return_type_is_frozenset() -> None:
    """Return type is frozenset, not set or list."""
    problems = [_p("ClassA", "f1", "HIGH")]
    result = classes_above_score_threshold(problems, {"HIGH": 3.0}, 1.0)
    assert type(result) is frozenset, (
        "Must be frozenset (not set/list); got " + repr(type(result))
    )


def test_empty_problems_returns_empty_frozenset() -> None:
    """Empty problems -> frozenset() (not raise)."""
    result = classes_above_score_threshold([], {"HIGH": 3.0}, 1.0)
    assert result == frozenset(), "Empty -> frozenset(); got " + repr(result)


def test_unknown_severity_contributes_zero_may_stay_below_threshold() -> None:
    """Unknown severity contributes 0; class stays below threshold.

    ClassA has only UNKNOWN_SEV (weight missing); threshold=0.5 -> frozenset().
    Kills impl that raises on missing weight key.
    """
    problems = [_p("ClassA", "f1", "UNKNOWN_SEV")]
    result = classes_above_score_threshold(problems, {"HIGH": 3.0}, 0.5)
    assert result == frozenset(), (
        "UNKNOWN_SEV contributes 0 -> ClassA score=0.0 <= 0.5; got " + repr(result)
    )
