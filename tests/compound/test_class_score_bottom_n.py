"""Item 570: class_score_bottom_n() -- bottom N classes by total weighted score (2026-06-08).

``class_score_bottom_n(problems, weights, n) -> list[str]``:
Returns the N lowest-scoring class names sorted ascending by score.
Complement of class_score_top_n (which returns highest scores).
Ties broken lexicographically.  Empty -> [].  n=0 -> [].  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns LOWEST-scoring classes (not highest).
     [A=10, B=5, C=1] n=2 -> ['C','B'] (ascending); top_n gives ['A','B'] (descending).
     Kills impl reusing class_score_top_n without reversal.
  2. n limits the list length (<= n).
     Kills impl returning all classes regardless of n.
  3. n=0 -> [] (not raise).
     Kills impl without n=0 guard.
  4. Empty problems -> [] (not raise).
     Kills impl without empty guard.
  5. Fewer than n classes -> return all (not raise).
     Kills impl that requires exactly n classes.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_score_bottom_n


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_lowest_not_highest() -> None:
    """PRIMARY DISC.: returns LOWEST-scoring classes, not highest.

    [A=10, B=5, C=1] with n=2:
    bottom_n=['C','B'] (ascending sort, lowest first)
    top_n would give ['A','B'] (descending sort, highest first)
    Kills impl reusing class_score_top_n on wrong sort direction.
    """
    problems = [
        _p("A", "f1", "HIGH"),    # A total = 10.0
        _p("B", "f2", "MEDIUM"),  # B total = 5.0
        _p("C", "f3", "LOW"),     # C total = 1.0
    ]
    weights = {"HIGH": 10.0, "MEDIUM": 5.0, "LOW": 1.0}
    result = class_score_bottom_n(problems, weights, 2)
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert len(result) == 2, f"n=2 -> 2 names; got {result}"
    # Bottom 2 by score = C(1.0) and B(5.0), NOT A(10.0) and B(5.0)
    assert "C" in result, (
        f"C (lowest=1.0) must be in bottom 2; got {result} "
        f"(['A','B'] = top_n is wrong -- kills class_score_top_n reuse)"
    )
    assert "B" in result, f"B (middle=5.0) must be in bottom 2; got {result}"
    assert "A" not in result, f"A (highest=10.0) must NOT be in bottom 2; got {result}"


def test_n_limits_list_length() -> None:
    """n caps the returned list length.

    Kills impl returning all classes regardless of n.
    """
    problems = [_p("A", "f1", "HIGH"), _p("B", "f2", "MEDIUM"), _p("C", "f3", "LOW")]
    weights = {"HIGH": 5.0, "MEDIUM": 3.0, "LOW": 1.0}
    result = class_score_bottom_n(problems, weights, 1)
    assert len(result) == 1, f"n=1 -> 1 class; got {result}"
    assert result[0] == "C", f"Bottom 1 class = C (score 1.0); got {result}"


def test_n_zero_returns_empty() -> None:
    """n=0 -> [] (not raise).

    Kills impl without n=0 guard.
    """
    problems = [_p("A", "f1", "HIGH")]
    result = class_score_bottom_n(problems, {"HIGH": 5.0}, 0)
    assert result == [], f"n=0 -> []; got {result}"


def test_empty_returns_empty_list() -> None:
    """Empty problems -> [] (not raise, not raise).

    Kills impl without empty guard.
    """
    result = class_score_bottom_n([], {"HIGH": 5.0}, 3)
    assert result == [], f"Empty -> []; got {result}"


def test_fewer_than_n_classes_returns_all() -> None:
    """Fewer than n classes -> return all available (not raise).

    Kills impl that requires exactly n classes or raises IndexError.
    """
    problems = [_p("A", "f1", "HIGH"), _p("B", "f2", "LOW")]
    weights = {"HIGH": 5.0, "LOW": 1.0}
    result = class_score_bottom_n(problems, weights, 10)
    assert len(result) == 2, f"2 classes with n=10 -> return both; got {result}"
    # B (1.0) comes before A (5.0) in ascending sort
    assert result[0] == "B", f"Ascending sort: B(1.0) first; got {result}"
    assert result[1] == "A", f"Ascending sort: A(5.0) second; got {result}"
