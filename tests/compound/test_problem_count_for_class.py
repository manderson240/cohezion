"""Item 396: problem_count_for_class() — record count for a specific class (2026-06-08).

``problem_count_for_class(problems, target_class) -> int``:
Returns the total number of Problem records where problem_class == target_class.
Returns 0 when the class is absent or problems is empty.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns an INTEGER count (not list, not frozenset, not None).
     Kills impl returning a list of matching Problem objects.
  2. Returns 0 when the target class is absent (not KeyError or None).
     Kills impl raising KeyError or returning None on miss.
  3. Counts ALL records for that class regardless of severity.
     Kills impl filtering out unlabelled records.
  4. Empty problems → 0.
     Kills impl raising on empty.
  5. Only counts the specified class, not all classes.
     Kills impl returning len(problems) or total histogram sum.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problem_count_for_class,
)


def _p(cls: str, fid: str = "f", sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_integer_count() -> None:
    """Returns an integer, not a list or frozenset.

    PRIMARY DISCRIMINATOR: kills impl returning matching Problem objects.
    """
    problems = [_p("alpha"), _p("alpha"), _p("beta")]
    result = problem_count_for_class(problems, "alpha")
    assert isinstance(result, int), "Must return int; got " + repr(type(result))
    assert result == 2, "alpha has 2 records; got " + repr(result)


def test_returns_zero_when_class_absent() -> None:
    """Returns 0 (not None, not KeyError) when target class is absent.

    Kills impl raising or returning None on miss.
    """
    problems = [_p("alpha"), _p("beta")]
    result = problem_count_for_class(problems, "gamma")
    assert result == 0, "gamma absent → 0; got " + repr(result)
    assert isinstance(result, int)


def test_counts_all_records_including_unlabelled() -> None:
    """Counts ALL records regardless of severity.

    Kills impl filtering out unlabelled (sev='') records.
    """
    problems = [
        _p("cls", sev="HIGH"),
        _p("cls", sev=""),   # unlabelled
        _p("cls", sev=""),   # unlabelled
    ]
    result = problem_count_for_class(problems, "cls")
    assert result == 3, "3 records (1 labelled + 2 unlabelled); got " + repr(result)


def test_empty_problems_returns_zero() -> None:
    """Empty problems list returns 0."""
    assert problem_count_for_class([], "any") == 0


def test_counts_only_specified_class() -> None:
    """Only the target class is counted, not all problems.

    Kills impl returning len(problems).
    """
    problems = [_p("alpha"), _p("beta"), _p("gamma"), _p("alpha")]
    result = problem_count_for_class(problems, "alpha")
    assert result == 2, "alpha appears twice; total=4; got " + repr(result)
    assert result != len(problems), "Must NOT return len(problems)"
