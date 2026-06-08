"""Item 576: class_problem_count_above() -- count of classes with > n problems (2026-06-08).

``class_problem_count_above(problems, n) -> int``:
Returns the count of distinct classes that have more than `n` problems.
Strict '>'.  0 for empty.  n=0 counts all classes with at least 1 problem.
Unweighted (ignores severity).  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns INT (not a list of class names).
     Kills impl returning class_score_above_threshold-style list.
  2. Strict '>' (not '>=') -- class with exactly n problems not counted.
     Kills impl using >=.
  3. 0 for empty problems list.
     Kills impl without empty guard.
  4. n=0 counts all classes (all have > 0 problems).
     Kills impl treating n=0 as a special empty case.
  5. Counts DISTINCT classes, not total problems.
     Kills impl counting problems instead of classes.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_problem_count_above


def _p(cls: str, fid: str, sev: str = "HIGH") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_int_not_list_primary_discriminator() -> None:
    """PRIMARY DISC.: returns INT (not a list of class names).

    3 classes: A(2 problems), B(3 problems), C(1 problem), n=1.
    Classes with > 1 problem: A, B -> count = 2 (int).
    Kills impl returning ['A','B'] (list like class_score_above_threshold).
    """
    problems = [
        _p("A", "f1"), _p("A", "f2"),         # A: 2 problems
        _p("B", "f1"), _p("B", "f2"), _p("B", "f3"),  # B: 3 problems
        _p("C", "f1"),                          # C: 1 problem
    ]
    result = class_problem_count_above(problems, 1)
    assert isinstance(result, int), (
        f"Must return int, not {type(result).__name__}; got {result!r} "
        f"(list return = class_score_above_threshold reuse is wrong)"
    )
    assert result == 2, (
        f"2 classes (A,B) have > 1 problem; got {result} "
        f"(3 = counting all classes is wrong)"
    )


def test_strict_greater_than_not_gte() -> None:
    """Strict '>' -- class with exactly n problems not counted.

    Class A has exactly 2 problems, n=2: A must NOT be counted.
    Class B has 3 problems, n=2: B must be counted.
    Kills impl using >= (would count A).
    """
    problems = [
        _p("A", "f1"), _p("A", "f2"),          # A: 2 problems (== n)
        _p("B", "f1"), _p("B", "f2"), _p("B", "f3"),  # B: 3 problems (> n)
    ]
    result = class_problem_count_above(problems, 2)
    assert result == 1, (
        f"Only B (3 > 2) counted; A (2 == 2) excluded; got {result} "
        f"(2 = impl uses >= instead of >)"
    )


def test_empty_returns_zero() -> None:
    """Empty problems -> 0 (not raise).

    Kills impl without empty guard.
    """
    result = class_problem_count_above([], 0)
    assert result == 0, f"Empty -> 0; got {result}"


def test_n_zero_counts_all_classes() -> None:
    """n=0 counts all classes (every class has > 0 problems).

    Kills impl treating n=0 as "return 0" or empty case.
    """
    problems = [_p("A", "f1"), _p("B", "f2"), _p("C", "f3")]
    result = class_problem_count_above(problems, 0)
    assert result == 3, (
        f"3 classes all have > 0 problems; n=0 should count all; got {result} "
        f"(0 = n=0 special-cased incorrectly)"
    )


def test_counts_distinct_classes_not_total_problems() -> None:
    """Counts distinct CLASSES, not total problems.

    10 problems all in class 'A' (n=5): count=1 (one class > 5 probs), not 10.
    Kills impl counting problems instead of classes.
    """
    problems = [_p("A", f"f{i}") for i in range(10)]  # A: 10 problems
    result = class_problem_count_above(problems, 5)
    assert result == 1, (
        f"One class (A with 10 problems > 5) -> count=1; got {result} "
        f"(10 = counting problems not classes is wrong)"
    )
