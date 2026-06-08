"""Item 577: fid_problem_count_above() -- count of fids with >n problems (2026-06-08).

``fid_problem_count_above(problems, n) -> int``:
Returns the count of distinct fids that appear in more than n problems.
FID-axis complement of class_problem_count_above.
Returns an int, not a list.  0 for empty.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on FID axis (not class axis).
     One class, three fids each appearing once: class_above(n=0)=1, fid_above(n=0)=3.
     Kills impl reusing class_problem_count_above (different axis).
  2. Returns COUNT (int) not a list of fid names.
     Kills impl returning a list.
  3. Strict '>' not '>=' -- fid with exactly n problems is excluded.
     Kills impl using >= threshold.
  4. 0 for empty problems.
     Kills impl without empty guard.
  5. n=0 counts all fids (every fid has > 0 problems).
     Kills impl treating n=0 as no-op.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_problem_count_above


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed on FID axis (not class axis).

    One class 'A', three fids [f1, f2, f3] each with 1 problem, n=0:
    class_above(n=0) = 1 (one class has > 0 problems)
    fid_above(n=0)   = 3 (three fids each have > 0 problems)
    Kills impl reusing class_problem_count_above.
    """
    problems = [
        _p("A", "f1", "HIGH"),
        _p("A", "f2", "HIGH"),
        _p("A", "f3", "HIGH"),
    ]
    result = fid_problem_count_above(problems, 0)
    assert isinstance(result, int), "Must return int; got " + repr(type(result))
    assert result == 3, (
        f"3 fids each with 1 problem, n=0: result=3; got {result} (1 = class axis, 3 = fid axis)"
    )


def test_returns_int_not_list() -> None:
    """Result is an int count, not a list of fid names.

    Kills impl returning list (like fid_score_above_threshold).
    """
    problems = [_p("A", "f1", "HIGH"), _p("B", "f2", "HIGH")]
    result = fid_problem_count_above(problems, 0)
    assert isinstance(result, int), f"Must return int; got {type(result)}"
    assert result == 2, f"2 fids with > 0 problems; got {result}"


def test_strict_greater_than_not_gte() -> None:
    """Strict '>' -- fid with exactly n problems is NOT counted.

    f1 has exactly 2 problems, n=2: f1 NOT counted (2 is not > 2).
    f2 has 3 problems, n=2: f2 IS counted (3 > 2).
    Kills impl using >= (would count f1).
    """
    problems = [
        _p("A", "f1", "H"),  # f1 appears 2 times
        _p("B", "f1", "H"),
        _p("C", "f2", "H"),  # f2 appears 3 times
        _p("D", "f2", "H"),
        _p("E", "f2", "H"),
    ]
    result = fid_problem_count_above(problems, 2)
    assert result == 1, (
        f"Only f2 (3 > 2) qualifies; f1 (2 == 2, not > 2) excluded; got {result} "
        f"(2 = >= instead of >)"
    )


def test_empty_returns_zero() -> None:
    """Empty problems -> 0 (not raise).

    Kills impl without empty guard.
    """
    result = fid_problem_count_above([], 0)
    assert result == 0, f"Empty -> 0; got {result}"


def test_n_zero_counts_all_fids() -> None:
    """n=0 counts all distinct fids (every fid has > 0 problems).

    Kills impl treating n=0 as a no-op (returning 0 when n=0).
    """
    problems = [_p("A", "f1", "H"), _p("B", "f2", "H"), _p("C", "f3", "H")]
    result = fid_problem_count_above(problems, 0)
    assert result == 3, f"n=0 -> all 3 fids counted (each has 1 > 0 problems); got {result}"
