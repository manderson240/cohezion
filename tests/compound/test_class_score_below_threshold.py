"""Item 574: class_score_below_threshold() -- classes with score < threshold (2026-06-08).

``class_score_below_threshold(problems, weights, threshold) -> list[str]``:
Returns class names whose total weighted score is strictly below `threshold`.
Complement of class_score_above_threshold (which uses > threshold).
Sorted ascending by score (then by class name for ties).
Empty -> [].  All-above-threshold -> [].  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns classes BELOW (not above) threshold.
     [A=10, B=5, C=1] threshold=6.0: below=['C','B'] (ascending), above=['A'].
     Kills impl reusing class_score_above_threshold (wrong direction).
  2. Strict '<' not '<=' -- class at exactly threshold is excluded.
     Kills impl using <= (includes boundary class).
  3. Empty problems -> [] (not raise).
     Kills impl without empty guard.
  4. All classes above threshold -> [].
     Kills impl always returning something.
  5. Result sorted ascending by score -- lowest-scoring class first.
     Kills impl returning descending or unsorted result.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_score_below_threshold


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_below_not_above_primary_discriminator() -> None:
    """PRIMARY DISC.: returns classes BELOW threshold (not above).

    [A=10, B=5, C=1] threshold=6.0:
    below=['C','B'] (ascending); above=['A'] (descending).
    Kills impl reusing class_score_above_threshold.
    """
    problems = [
        _p("A", "f1", "HIGH"),  # A total = 10.0
        _p("B", "f2", "MEDIUM"),  # B total = 5.0
        _p("C", "f3", "LOW"),  # C total = 1.0
    ]
    weights = {"HIGH": 10.0, "MEDIUM": 5.0, "LOW": 1.0}
    result = class_score_below_threshold(problems, weights, 6.0)
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert "B" in result, f"B (5.0 < 6.0) must be included; got {result}"
    assert "C" in result, f"C (1.0 < 6.0) must be included; got {result}"
    assert "A" not in result, (
        f"A (10.0 not < 6.0) must be excluded; got {result} "
        f"('A' present = above_threshold direction is wrong)"
    )
    assert len(result) == 2, f"Exactly 2 classes below 6.0; got {result}"


def test_strict_less_than_not_lte() -> None:
    """Strict '<' -- class at exactly threshold is excluded.

    Class_at score=5.0, threshold=5.0: must NOT appear.
    Class_below score=1.0, threshold=5.0: must appear.
    Kills impl using <= (would include class_at).
    """
    problems = [
        _p("AtThreshold", "f1", "FIVE"),  # score = 5.0
        _p("BelowThreshold", "f2", "ONE"),  # score = 1.0
    ]
    weights = {"FIVE": 5.0, "ONE": 1.0}
    result = class_score_below_threshold(problems, weights, 5.0)
    assert "BelowThreshold" in result, f"BelowThreshold (1.0 < 5.0) must be included; got {result}"
    assert "AtThreshold" not in result, (
        f"AtThreshold (5.0 == threshold) must be EXCLUDED by strict <; got {result} "
        f"(found AtThreshold -> impl uses <= instead of <)"
    )


def test_empty_returns_empty_list() -> None:
    """Empty problems -> [] (not raise).

    Kills impl without empty guard.
    """
    result = class_score_below_threshold([], {"HIGH": 5.0}, 10.0)
    assert result == [], f"Empty -> []; got {result}"


def test_all_above_threshold_returns_empty() -> None:
    """All classes above threshold -> [].

    Kills impl always returning something.
    """
    problems = [_p("A", "f1", "HIGH"), _p("B", "f2", "HIGH")]
    weights = {"HIGH": 10.0}
    result = class_score_below_threshold(problems, weights, 5.0)
    assert result == [], f"All scores (10.0) above threshold (5.0) -> []; got {result}"


def test_result_sorted_ascending_by_score() -> None:
    """Result sorted ascending by score (lowest-scoring class first).

    Kills impl returning descending or unsorted result.
    """
    problems = [
        _p("A", "f1", "LOW"),  # A total = 1.0
        _p("B", "f2", "HIGH"),  # B total = 10.0
        _p("C", "f3", "MED"),  # C total = 5.0
    ]
    weights = {"LOW": 1.0, "MED": 5.0, "HIGH": 10.0}
    # threshold=15.0 -> all three qualify (all < 15.0); ascending: A(1) < C(5) < B(10)
    result = class_score_below_threshold(problems, weights, 15.0)
    assert result == ["A", "C", "B"], (
        f"Ascending sort: A(1) < C(5) < B(10); got {result} (descending or unsorted is wrong)"
    )
