"""Item 484: all_severity_scores() -- total severity score for every class (2026-06-08).

``all_severity_scores(problems, weights) -> dict[str, float]``:
Returns dict[class_name -> total_severity_score] for every class in problems.
Uses the same weight map as class_total_severity_score.  Classes with score=0.0
still appear if they are present in problems.  Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns dict keyed by class (not by fid).
     ClassA score=7.0, ClassB score=3.0 -> {'ClassA': 7.0, 'ClassB': 3.0}.
     Kills impl reusing fid_total_severity_score path (wrong key axis).
  2. Score is weighted sum not count.
     ClassA: HIGH x2 weight=3.0 + LOW x1 weight=1.0 -> 7.0, not 3.
     Kills impl returning plain problem count per class.
  3. Class present even if score=0.0 (all unknown severities).
     Kills impl that omits zero-score classes (sparse would miss them).
  4. Empty problems -> {}.
     Kills impl with unguarded access.
  5. Unknown severity contributes 0.
     Kills impl raising KeyError.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    all_severity_scores,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_dict_keyed_by_class_not_fid() -> None:
    """PRIMARY DISC.: dict keyed by class name.

    ClassA score=7.0, ClassB score=3.0.
    Kills impl reusing fid_total_severity_score (wrong axis).
    """
    problems = [
        _p("ClassA", "fid_a", "HIGH"),
        _p("ClassA", "fid_b", "HIGH"),
        _p("ClassA", "fid_c", "LOW"),
        _p("ClassB", "fid_a", "HIGH"),
    ]
    weights = {"HIGH": 3.0, "LOW": 1.0}
    result = all_severity_scores(problems, weights)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert result.get("ClassA") == 7.0, "ClassA=7.0; got " + repr(result)
    assert result.get("ClassB") == 3.0, "ClassB=3.0; got " + repr(result)
    assert "fid_a" not in result, "Keys must be classes not fids; got " + repr(result)


def test_score_is_weighted_sum_not_count() -> None:
    """Weighted sum, not plain count.

    ClassA: HIGH x2 weight=3.0, LOW x1 weight=1.0 -> 7.0 (not 3).
    Kills impl returning count per class.
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),
        _p("ClassA", "f2", "HIGH"),
        _p("ClassA", "f3", "LOW"),
    ]
    result = all_severity_scores(problems, {"HIGH": 3.0, "LOW": 1.0})
    assert result["ClassA"] == 7.0, "7.0 not 3; got " + repr(result)


def test_zero_score_class_still_present() -> None:
    """Class with only unknown severities -> score=0.0 but still in result.

    Kills impl omitting zero-score classes.
    """
    problems = [
        _p("ClassA", "f1", "UNKNOWN"),
        _p("ClassB", "f2", "HIGH"),
    ]
    result = all_severity_scores(problems, {"HIGH": 5.0})
    assert "ClassA" in result, "ClassA must appear even with score=0.0; got " + repr(result)
    assert result["ClassA"] == 0.0, "ClassA score=0.0; got " + repr(result)


def test_empty_problems_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise)."""
    result = all_severity_scores([], {"HIGH": 3.0})
    assert result == {}, "Empty -> {}; got " + repr(result)


def test_unknown_severity_contributes_zero() -> None:
    """Unknown severity contributes 0 (not raise)."""
    problems = [
        _p("ClassA", "f1", "HIGH"),
        _p("ClassA", "f2", "MYSTERY"),
    ]
    result = all_severity_scores(problems, {"HIGH": 4.0})
    assert result["ClassA"] == 4.0, "MYSTERY contributes 0; got " + repr(result)
