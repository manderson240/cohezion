"""Item 355: count_problems_with_severity() -- count of labelled problems (2026-06-08).

``count_problems_with_severity(problems) -> int``:
Returns the number of Problem records with non-empty severity.
Equivalent to len(labelled_problems(problems)).  Empty -> 0.  Pure; no I/O.

Discriminating tests:

  1. PRIMARY DISC.: returns an INTEGER not a list.
     Kills impl returning labelled_problems list.
  2. Unlabelled problems excluded from count.
     Kills impl counting all problems.
  3. Result equals len(labelled_problems(problems)) — invariant check.
     Kills impl with arithmetic off-by-one.
  4. Empty input returns 0 not error.
     Kills impl raising on empty.
  5. All-unlabelled returns 0.
     Kills impl counting based on non-empty class names.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    count_problems_with_severity,
    labelled_problems,
)


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


def test_returns_integer_not_list() -> None:
    """Returns int, not a list.

    PRIMARY DISCRIMINATOR: kills impl returning labelled_problems list.
    """
    problems = [_ps("a", 0, "HIGH"), _p("b", 0)]
    result = count_problems_with_severity(problems)
    assert isinstance(result, int), "Must return int; got " + repr(type(result))
    assert result == 1, "1 labelled; got " + repr(result)


def test_unlabelled_excluded() -> None:
    """Unlabelled excluded from count.

    Kills impl counting all problems.
    3 labelled + 2 unlabelled -> 3.
    """
    problems = [_ps("a", i, "HIGH") for i in range(3)] + [_p("b", i) for i in range(2)]
    assert count_problems_with_severity(problems) == 3


def test_equals_len_labelled_problems_invariant() -> None:
    """count == len(labelled_problems(problems)) for any input."""
    problems = [_ps("a", 0, "HIGH"), _p("b", 0), _ps("c", 0, "LOW"), _p("d", 0)]
    expected = len(labelled_problems(problems))
    result = count_problems_with_severity(problems)
    assert result == expected, f"Must equal len(labelled_problems)={expected}; got {result}"


def test_empty_returns_zero() -> None:
    """Empty input returns 0."""
    assert count_problems_with_severity([]) == 0


def test_all_unlabelled_returns_zero() -> None:
    """All-unlabelled input returns 0."""
    problems = [_p("a", i) for i in range(5)]
    assert count_problems_with_severity(problems) == 0
