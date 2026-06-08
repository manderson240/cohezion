"""Item 578: class_problem_count_below() -- count of classes with <n problems (2026-06-08).

``class_problem_count_below(problems, n) -> int``:
Returns the count of distinct classes that have strictly fewer than n problems.
Complement of class_problem_count_above.
Returns an int.  0 for empty.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns classes with FEWER THAN n problems (complement of >n).
     [A=3 problems, B=1 problem] n=2: only B qualifies (1 < 2); result=1.
     Kills impl reusing class_problem_count_above (opposite direction).
  2. Strict '<' not '<=' -- class with exactly n problems is NOT counted.
     [A=2, B=3] n=2: neither has < 2 -> result=0 (A has == 2, excluded).
     Kills impl using <=.
  3. Returns INT not list.
     Kills impl returning a list of class names.
  4. Empty -> 0 (not raise).
     Kills impl without empty guard.
  5. n=1 returns 0 (no class can have < 1 problem -- every class has at least 1).
     Kills impl that counts classes with 0 problems (impossible from input).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_problem_count_below


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_counts_classes_below_not_above_primary_discriminator() -> None:
    """PRIMARY DISC.: counts classes with fewer than n, not more than n.

    [A=3, B=1] n=2: B(1 < 2) counted, A(3 not < 2) excluded; result=1.
    class_problem_count_above(n=2) would count A (3 > 2), not B.
    Kills impl reusing class_problem_count_above.
    """
    problems = [
        _p("A", "f1", "H"),  # A: 3 problems
        _p("A", "f2", "H"),
        _p("A", "f3", "H"),
        _p("B", "f4", "H"),  # B: 1 problem
    ]
    result = class_problem_count_below(problems, 2)
    assert isinstance(result, int), "Must return int; got " + repr(type(result))
    assert result == 1, (
        f"Only B (count=1 < 2) qualifies; A (count=3) excluded; got {result} "
        f"(1 = wrong, likely counting >2 instead of <2)"
    )


def test_strict_less_than_not_lte() -> None:
    """Strict '<' -- class with exactly n problems is NOT counted.

    [A=2, B=3] n=2: A(2 not < 2) excluded, B(3 not < 2) excluded -> result=0.
    Kills impl using <= (would count A).
    """
    problems = [
        _p("A", "f1", "H"),  # A: 2 problems
        _p("A", "f2", "H"),
        _p("B", "f3", "H"),  # B: 3 problems
        _p("B", "f4", "H"),
        _p("B", "f5", "H"),
    ]
    result = class_problem_count_below(problems, 2)
    assert result == 0, (
        f"No class has < 2 problems (A has 2, not strictly below); got {result} "
        f"(1 = <= used instead of <)"
    )


def test_returns_int_not_list() -> None:
    """Result is int count, not a list of class names.

    Kills impl returning a list.
    """
    problems = [_p("A", "f1", "H"), _p("B", "f2", "H")]
    result = class_problem_count_below(problems, 2)
    assert isinstance(result, int), f"Must return int; got {type(result)}"
    assert result == 2, f"Both A and B have 1 < 2 problems; got {result}"


def test_empty_returns_zero() -> None:
    """Empty problems -> 0 (not raise).

    Kills impl without empty guard.
    """
    result = class_problem_count_below([], 5)
    assert result == 0, f"Empty -> 0; got {result}"


def test_n_one_returns_zero() -> None:
    """n=1: no class can have < 1 problems (all classes have at least 1).

    Every class in problems has at least 1 problem by definition.
    Kills impl accidentally counting classes with 0 problems.
    """
    problems = [_p("A", "f1", "H"), _p("B", "f2", "H")]
    result = class_problem_count_below(problems, 1)
    assert result == 0, f"n=1: no class has < 1 problems; got {result}"
