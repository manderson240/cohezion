"""Item 196: most_frequent_class() — dominant-class accessor (2026-06-08).

``most_frequent_class(problems: list[Problem])`` -> ``str | None``:
Returns the ``problem_class`` string with the highest count among all
findings.  On ties the FIRST-OCCURRENCE class wins (insertion order of
first appearance).  Empty list -> ``None``.  Pure; no I/O.

Enables hotspot detection without unpacking a Counter::

    if cls := most_frequent_class(findings):
        flag_class(cls)

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: non-empty list -> most-frequent class string returned.
     Kills an impl that returns the count int or always returns None.
  2. Tie -> FIRST-OCCURRENCE class wins.
     Kills an impl that returns the last-seen class on ties.
  3. Empty list -> None (no raises).
     Kills an impl that raises ValueError on empty input.
  4. Return type is str, not int.
     Kills an impl that returns the count instead of the class name.
  5. Single-class list -> that class (not None).
     Kills an impl that requires >= 2 distinct classes.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    most_frequent_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_most_frequent_class_returned() -> None:
    """Non-empty list -> the class with the highest count.

    PRIMARY DISCRIMINATOR: kills an impl that returns None, returns the
    count int, or returns an arbitrary class regardless of frequency.
    """
    problems = [
        _p("beta"),
        _p("alpha", 0),
        _p("beta", 1),
        _p("beta", 2),
    ]  # beta: 3, alpha: 1

    result = most_frequent_class(problems)

    assert result == "beta", "Most frequent class must be 'beta'; got " + repr(result)


def test_tie_broken_by_first_occurrence() -> None:
    """Two classes with equal count -> first-occurrence class returned.

    Kills an impl that returns the last-seen class on ties (e.g. by
    iterating and overwriting instead of returning on first max).
    'alpha' appears first and must win the tie over 'beta'.
    """
    problems = [
        _p("alpha", 0),
        _p("beta", 0),
        _p("alpha", 1),
        _p("beta", 1),
    ]  # both classes have count 2; alpha appears first

    result = most_frequent_class(problems)

    assert result == "alpha", "Tie must be broken by first occurrence ('alpha' first); got " + repr(
        result
    )


def test_empty_list_returns_none() -> None:
    """Empty list -> None (no raises).

    Kills an impl that raises ValueError on empty input.
    """
    result = most_frequent_class([])

    assert result is None, "Empty input must return None; got " + repr(result)


def test_return_type_is_str_not_int() -> None:
    """Return value is the class string, not the count integer.

    Kills an impl that returns the frequency count (an int) rather than
    the class name (a str).
    """
    problems = [_p("nesting_outlier"), _p("nesting_outlier", 1)]

    result = most_frequent_class(problems)

    assert isinstance(result, str), "Return type must be str; got " + str(type(result))
    assert result == "nesting_outlier", "Must be the class name; got " + repr(result)


def test_single_class_list_returns_that_class() -> None:
    """All findings share one class -> that class returned (not None).

    Kills an impl that returns None unless >= 2 distinct classes are present.
    """
    problems = [_p("complexity_outlier", i) for i in range(4)]

    result = most_frequent_class(problems)

    assert result == "complexity_outlier", "Single-class list must return that class; got " + repr(
        result
    )
