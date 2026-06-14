"""Item 236: sample_problems_by_class() — up to N problems per class (2026-06-08).

``sample_problems_by_class(problems: list[Problem], n: int = 5)``
-> ``dict[str, list[Problem]]``:
Returns at most *n* Problem objects per class (first *n* in original order).
Useful when a class has many findings and full listing is impractical.
Empty input → {}.  Pure; no I/O.

Distinct from ``group_problems_by_class`` (returns ALL problems per class).

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: each class has at most n problems.
     Kills impl delegating to group_problems_by_class unchanged.
  2. Insertion order preserved within each sample.
     Kills impl that reverses or sorts the sample.
  3. Class absent from result when it has 0 problems.
     Kills impl that always includes all monitored classes.
  4. Full list returned when class has fewer than n problems.
     Kills impl that always pads to exactly n.
  5. n=0 yields empty lists per present class.
     Kills impl that excludes the class when n=0.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    sample_problems_by_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_each_class_has_at_most_n_problems() -> None:
    """Each class in result has at most n problems.

    PRIMARY DISCRIMINATOR: kills impl that returns all problems per class.
    alpha has 10 problems, n=3 -> result has exactly 3 alpha problems.
    """
    problems = [_p("alpha", i) for i in range(10)]

    result = sample_problems_by_class(problems, n=3)

    assert len(result["alpha"]) == 3, (
        "alpha has 10 problems, n=3 -> sample must have 3; got " + repr(len(result["alpha"]))
    )


def test_insertion_order_preserved_in_sample() -> None:
    """Problems appear in original input order within each sample.

    Kills impl that reverses or sorts the sample.
    """
    problems = [_p("alpha", i) for i in range(8)]

    result = sample_problems_by_class(problems, n=4)

    expected = problems[:4]
    assert result["alpha"] == expected, "First 4 alpha problems must be in order; got " + repr(
        result["alpha"]
    )


def test_absent_class_not_in_result() -> None:
    """Class with no problems is absent from result.

    Kills impl that always includes all possible classes.
    """
    problems = [_p("alpha")]
    # beta has no problems at all

    result = sample_problems_by_class(problems, n=5)

    assert "alpha" in result
    assert "beta" not in result, "beta (no problems) must be absent; got " + repr(result)


def test_fewer_than_n_returns_all() -> None:
    """When class has fewer problems than n, all are returned (no padding).

    Kills impl that always pads to exactly n.
    alpha has 2 problems, n=5 -> all 2 returned.
    """
    problems = [_p("alpha", i) for i in range(2)]

    result = sample_problems_by_class(problems, n=5)

    assert len(result["alpha"]) == 2, (
        "alpha has 2 problems < n=5; all 2 must be returned; got " + repr(len(result["alpha"]))
    )


def test_n_zero_yields_empty_list_per_present_class() -> None:
    """n=0 yields an empty list for each class that has problems.

    Kills impl that excludes the class entirely when n=0.
    """
    problems = [_p("alpha", i) for i in range(5)] + [_p("beta", i) for i in range(3)]

    result = sample_problems_by_class(problems, n=0)

    assert "alpha" in result, "alpha must be present even with n=0; got " + repr(result)
    assert result["alpha"] == [], "n=0 -> empty list for alpha; got " + repr(result["alpha"])
    assert "beta" in result, "beta must be present even with n=0; got " + repr(result)
    assert result["beta"] == [], "n=0 -> empty list for beta; got " + repr(result["beta"])
