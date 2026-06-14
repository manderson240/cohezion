"""Item 579: fid_problem_count_below() -- count of fids with <n problems (2026-06-08).

``fid_problem_count_below(problems, n) -> int``:
Returns the count of distinct fids that appear in strictly fewer than n problems.
FID-axis complement of class_problem_count_below.
Returns an int.  0 for empty.  n=1 -> always 0.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on FID axis (not class axis).
     One class, three fids each appearing once, n=2:
     class_below(n=2)=1 (one class with 1 < 2 problems)
     fid_below(n=2)=3 (three fids each with 1 < 2 problems)
     Kills impl reusing class_problem_count_below (different axis).
  2. Strict '<' not '<=' -- fid with exactly n problems excluded.
     [f1 appears 2x] n=2: f1 not counted (2 not < 2) -> 0.
     Kills impl using <=.
  3. Returns INT not list.
     Kills impl returning a list.
  4. Empty -> 0 (not raise).
     Kills impl without empty guard.
  5. n=1 returns 0 (all fids have at least 1 problem by definition).
     Kills impl counting fids with 0 problems (impossible).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_problem_count_below


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed on FID axis (not class axis).

    One class 'A', three fids [f1, f2, f3] each with 1 problem, n=2:
    class_below(n=2) = 1 (class A has 3 problems... wait no -- A has 3 total,
    but that's wrong). Let me use a cleaner example:
    3 separate classes each with 1 fid appearing once, n=2:
    class_below(n=2) = 3 classes each with 1 < 2 problems.
    fid_below(n=2) = same 3 fids each with 1 < 2 problems.
    But with 1 class, 3 fids:
    class_below(n=2) = 1 (class A has 3 total, but fid axis is different).
    Wait: class A has 3 problems (f1+f2+f3). So class_below(n=2)=0 (3 not < 2).
    fid_below(n=2) = 3 (each fid has 1 < 2 problems). DISCRIMINATING!
    Kills impl reusing class_problem_count_below.
    """
    problems = [
        _p("A", "f1", "H"),  # f1: 1 problem; class A: 3 total
        _p("A", "f2", "H"),  # f2: 1 problem
        _p("A", "f3", "H"),  # f3: 1 problem
    ]
    result = fid_problem_count_below(problems, 2)
    assert isinstance(result, int), "Must return int; got " + repr(type(result))
    assert result == 3, (
        f"3 fids each with 1 < 2 problems; class_below would give 0 (A has 3 problems); "
        f"got {result} (0 = class axis wrong)"
    )


def test_strict_less_than_not_lte() -> None:
    """Strict '<' -- fid with exactly n problems is NOT counted.

    f1 appears exactly 2 times, n=2: f1 NOT counted (2 not < 2) -> 0.
    Kills impl using <= (would count f1).
    """
    problems = [
        _p("A", "f1", "H"),  # f1: 2 problems
        _p("B", "f1", "H"),
    ]
    result = fid_problem_count_below(problems, 2)
    assert result == 0, (
        f"f1 has 2 problems, threshold=2 (strict <): not below; got {result} "
        f"(1 = <= used instead of <)"
    )


def test_returns_int_not_list() -> None:
    """Result is int count, not a list of fid names.

    Kills impl returning a list.
    """
    problems = [_p("A", "f1", "H"), _p("B", "f2", "H")]
    result = fid_problem_count_below(problems, 2)
    assert isinstance(result, int), f"Must return int; got {type(result)}"
    assert result == 2, f"Both f1 and f2 have 1 < 2 problems; got {result}"


def test_empty_returns_zero() -> None:
    """Empty problems -> 0 (not raise).

    Kills impl without empty guard.
    """
    result = fid_problem_count_below([], 5)
    assert result == 0, f"Empty -> 0; got {result}"


def test_n_one_returns_zero() -> None:
    """n=1: no fid can have < 1 problems (all fids have at least 1).

    Every fid in problems appears at least once by definition.
    Kills impl accidentally counting fids with 0 problems.
    """
    problems = [_p("A", "f1", "H"), _p("B", "f2", "H")]
    result = fid_problem_count_below(problems, 1)
    assert result == 0, f"n=1: no fid has < 1 problems; got {result}"
