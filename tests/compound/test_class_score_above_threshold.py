"""Item 572: class_score_above_threshold() -- classes with score > threshold (2026-06-08).

``class_score_above_threshold(problems, weights, threshold) -> list[str]``:
Returns class names whose total weighted score strictly exceeds `threshold`.
Sorted descending by score (then by name for ties).
Empty -> [].  All-below-threshold -> [].  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: strict '>' not '>=' -- threshold=5.0, class scoring exactly 5.0 excluded.
     Kills impl using >= (off-by-one on equality boundary).
  2. Filters on score threshold, not count -- [A=10, B=5, C=1] threshold=4.0: ['A','B'] not ['A','B','C'].
     Kills impl ignoring the threshold parameter.
  3. Empty problems -> [] (not raise).
     Kills impl without empty guard.
  4. All classes below threshold -> [] (not raise).
     Kills impl always returning something.
  5. Result sorted descending by score -- highest-scoring class first.
     Kills impl returning unsorted or ascending result.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_score_above_threshold


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_strict_greater_than_not_gte_primary_discriminator() -> None:
    """PRIMARY DISC.: strict '>' threshold -- class at exactly threshold is excluded.

    Class A score=5.0, threshold=5.0: A must NOT appear.
    Class B score=10.0, threshold=5.0: B must appear.
    Kills impl using >= (would include A).
    """
    problems = [
        _p("A", "f1", "FIVE"),   # A total = 5.0
        _p("B", "f2", "TEN"),    # B total = 10.0
    ]
    weights = {"FIVE": 5.0, "TEN": 10.0}
    result = class_score_above_threshold(problems, weights, 5.0)
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert "B" in result, (
        f"B (10.0 > 5.0) must be included; got {result}"
    )
    assert "A" not in result, (
        f"A (5.0 == threshold) must be EXCLUDED by strict >; got {result} "
        f"(found A -> impl uses >= instead of >)"
    )


def test_filters_by_score_not_count() -> None:
    """Threshold filters by score, not problem count.

    [A=10, B=5, C=1] threshold=4.0: result=['A','B'] (both > 4.0), not all three.
    Kills impl ignoring the threshold parameter.
    """
    problems = [
        _p("A", "f1", "HIGH"),    # A total = 10.0
        _p("B", "f2", "MEDIUM"),  # B total = 5.0
        _p("C", "f3", "LOW"),     # C total = 1.0
    ]
    weights = {"HIGH": 10.0, "MEDIUM": 5.0, "LOW": 1.0}
    result = class_score_above_threshold(problems, weights, 4.0)
    assert "A" in result and "B" in result, f"A(10) and B(5) both > 4.0; got {result}"
    assert "C" not in result, (
        f"C (1.0) not > 4.0, must be excluded; got {result} "
        f"(C present = threshold ignored)"
    )
    assert len(result) == 2, f"Exactly 2 classes above 4.0; got {result}"


def test_empty_returns_empty_list() -> None:
    """Empty problems -> [] (not raise).

    Kills impl without empty guard.
    """
    result = class_score_above_threshold([], {"HIGH": 5.0}, 0.0)
    assert result == [], f"Empty -> []; got {result}"


def test_all_below_threshold_returns_empty() -> None:
    """All classes below threshold -> [].

    Kills impl that always returns something.
    """
    problems = [_p("A", "f1", "LOW"), _p("B", "f2", "LOW")]
    weights = {"LOW": 1.0}
    result = class_score_above_threshold(problems, weights, 5.0)
    assert result == [], f"All scores (1.0) below threshold (5.0) -> []; got {result}"


def test_result_sorted_descending_by_score() -> None:
    """Result sorted descending by score (highest-scoring class first).

    Kills impl returning unsorted or ascending result.
    """
    problems = [
        _p("A", "f1", "LOW"),    # A total = 1.0
        _p("B", "f2", "HIGH"),   # B total = 10.0
        _p("C", "f3", "MED"),    # C total = 5.0
    ]
    weights = {"LOW": 1.0, "MED": 5.0, "HIGH": 10.0}
    result = class_score_above_threshold(problems, weights, 0.5)
    # All three exceed 0.5; descending order: B(10) > C(5) > A(1)
    assert result == ["B", "C", "A"], (
        f"Descending sort: B(10) > C(5) > A(1); got {result} "
        f"(ascending or unsorted order is wrong)"
    )
