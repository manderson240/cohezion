"""Item 215: most_common_class() — single most-frequent class (2026-06-08).

``most_common_class(problems: list[Problem])``
-> ``str | None``:
Returns the ``problem_class`` with the highest finding count.
Tie -> first-seen class wins.
Empty list -> ``None``.  Pure; no I/O.

Scalar top-1 accessor — avoids building a count dict externally::

    top = most_common_class(findings)   # "complexity_outlier"

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns the class NAME, not the count.
     Kills an impl that returns max(counts.values()) (the integer count).
  2. Tie -> first-seen class wins (not alphabetical, not last).
     Kills an impl that uses max(key=lambda c: counts[c]) on an unordered
     dict, or that sorts alphabetically.
  3. Empty list -> None (not raises, not "").
     Kills an impl that raises on empty input.
  4. Single-class list -> that class.
     Kills an impl that requires multiple classes.
  5. Return type is str | None.
     Kills an impl that returns an int or a list.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    most_common_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_class_name_not_count() -> None:
    """Returns the class NAME with the most findings, not the count.

    PRIMARY DISCRIMINATOR: kills an impl that returns max(counts.values()),
    i.e. the integer 5 instead of the string 'complexity_outlier'.
    """
    problems = [_p("complexity_outlier", i) for i in range(5)]
    problems += [_p("nesting_outlier", i) for i in range(2)]

    result = most_common_class(problems)

    assert isinstance(result, str), "return type must be str; got " + repr(type(result))
    assert result == "complexity_outlier", "class with count=5 must win; got " + repr(result)


def test_tie_broken_by_first_occurrence() -> None:
    """Tie in count -> first-seen class wins (not alphabetical).

    Kills an impl that picks alphabetically (would return 'alpha' here
    since 'zeta' > 'alpha' alphabetically, but 'zeta' appears first).
    Both 'zeta' and 'alpha' have count=2; 'zeta' appears first.
    """
    problems = [
        _p("zeta", 0),
        _p("zeta", 1),  # count=2
        _p("alpha", 0),
        _p("alpha", 1),  # count=2
    ]

    result = most_common_class(problems)

    assert result == "zeta", (
        "tie must be broken by first occurrence ('zeta' before 'alpha'); got " + repr(result)
    )


def test_empty_list_returns_none() -> None:
    """Empty list -> None (not raises, not '').

    Kills an impl that raises ValueError or returns empty string.
    """
    result = most_common_class([])

    assert result is None, "empty input must return None; got " + repr(result)


def test_single_class_returns_that_class() -> None:
    """Single class in problems -> that class.

    Kills an impl that requires >= 2 distinct classes to work.
    """
    problems = [_p("alpha", i) for i in range(3)]

    result = most_common_class(problems)

    assert result == "alpha", "single class must be returned; got " + repr(result)


def test_distinct_winner_among_multiple_classes() -> None:
    """Class with clearly highest count wins.

    Kills an impl that returns first class regardless of count.
    beta has count=1, alpha has count=4 -> alpha must win.
    """
    problems = [_p("beta", 0)] + [_p("alpha", i) for i in range(4)]

    result = most_common_class(problems)

    assert result == "alpha", "alpha (count=4) must win over beta (count=1); got " + repr(result)
