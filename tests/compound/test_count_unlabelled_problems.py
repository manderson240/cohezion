"""Item 356: count_unlabelled_problems() -- count of unlabelled problems (2026-06-08).

``count_unlabelled_problems(problems) -> int``:
Returns the number of Problem records with severity == ''.
Equivalent to len(unlabelled_problems(problems)).  Empty -> 0.  Pure; no I/O.
Together with count_problems_with_severity provides the full partition.

Discriminating tests:

  1. PRIMARY DISC.: returns INTEGER not list.
     Kills impl returning unlabelled_problems list.
  2. Labelled problems not counted.
     Kills impl counting all or counting labelled.
  3. Partition invariant: count_problems_with_severity + count_unlabelled == len.
     Kills impl with off-by-one in complement arithmetic.
  4. Empty returns 0.
     Kills impl raising on empty.
  5. All-labelled returns 0.
     Kills impl always returning a positive count.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    count_problems_with_severity,
    count_unlabelled_problems,
)


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


def test_returns_integer_not_list() -> None:
    """Returns int, not a list.

    PRIMARY DISCRIMINATOR: kills impl returning unlabelled_problems list.
    """
    problems = [_p("a", 0), _ps("b", 0, "HIGH")]
    result = count_unlabelled_problems(problems)
    assert isinstance(result, int), "Must return int; got " + repr(type(result))
    assert result == 1, "1 unlabelled; got " + repr(result)


def test_labelled_problems_not_counted() -> None:
    """Labelled problems are excluded from count.

    Kills impl counting all problems.
    2 labelled + 3 unlabelled -> 3.
    """
    problems = (
        [_ps("a", i, "HIGH") for i in range(2)]
        + [_p("b", i) for i in range(3)]
    )
    assert count_unlabelled_problems(problems) == 3


def test_partition_invariant() -> None:
    """count_with + count_without == len(problems) for any input.

    Kills off-by-one in complement arithmetic.
    """
    problems = [_p("a", 0), _ps("b", 0, "HIGH"), _p("c", 0), _ps("d", 0, "LOW")]
    total = len(problems)
    with_sev = count_problems_with_severity(problems)
    without_sev = count_unlabelled_problems(problems)
    assert with_sev + without_sev == total, (
        f"Partition: {with_sev}+{without_sev}={with_sev+without_sev} \!= {total}"
    )


def test_empty_returns_zero() -> None:
    """Empty input returns 0."""
    assert count_unlabelled_problems([]) == 0


def test_all_labelled_returns_zero() -> None:
    """All-labelled input returns 0."""
    problems = [_ps("a", i, "HIGH") for i in range(5)]
    assert count_unlabelled_problems(problems) == 0
