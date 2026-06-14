"""Item 197: least_frequent_class() — rarest-class accessor (2026-06-08).

``least_frequent_class(problems: list[Problem])`` -> ``str | None``:
Returns the ``problem_class`` string with the LOWEST count among all
findings.  On ties the LAST-OCCURRENCE class wins (most-recent final
sighting).  Empty list -> ``None``.  Pure; no I/O.

Symmetric complement of :func:`most_frequent_class` for tail-class
analysis (finding the rarest, most-easily-missed class type)::

    if cls := least_frequent_class(findings):
        audit_rare_class(cls)

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: non-empty list -> least-frequent class string.
     Kills an impl that returns the most-frequent class or always None.
  2. Tie -> LAST-OCCURRENCE class wins.
     Kills an impl that returns first-occurrence (same as most_frequent).
  3. Empty list -> None (no raises).
     Kills an impl that raises ValueError on empty input.
  4. Return type is str, not int.
     Kills an impl that returns the count instead of the class name.
  5. Single distinct class -> that class (not None).
     Kills an impl that requires >= 2 distinct classes.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    least_frequent_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_least_frequent_class_returned() -> None:
    """Non-empty list -> the class with the lowest count.

    PRIMARY DISCRIMINATOR: kills an impl that returns the most-frequent
    class (e.g. a copy-paste of most_frequent_class), or always None.
    """
    problems = [
        _p("alpha", 0),
        _p("beta"),
        _p("alpha", 1),
        _p("alpha", 2),
    ]  # alpha: 3, beta: 1

    result = least_frequent_class(problems)

    assert result == "beta", "Least frequent class must be 'beta'; got " + repr(result)


def test_tie_broken_by_last_occurrence() -> None:
    """Two classes with equal count -> LAST-occurrence class returned.

    Kills an impl that returns first-occurrence (mirroring most_frequent)
    rather than last-occurrence.
    'beta' has its final appearance after 'alpha', so 'beta' must win.
    """
    problems = [
        _p("alpha", 0),
        _p("beta", 0),
        _p("alpha", 1),
        _p("beta", 1),
    ]  # both have count 2; beta's last index (3) > alpha's last index (2)

    result = least_frequent_class(problems)

    assert result == "beta", "Tie must be broken by last occurrence ('beta' last); got " + repr(
        result
    )


def test_empty_list_returns_none() -> None:
    """Empty list -> None (no raises).

    Kills an impl that raises ValueError on empty input.
    """
    result = least_frequent_class([])

    assert result is None, "Empty input must return None; got " + repr(result)


def test_return_type_is_str_not_int() -> None:
    """Return value is the class string, not the count integer.

    Kills an impl that returns the frequency count (an int) rather than
    the class name (a str).
    """
    problems = [_p("nesting_outlier")]

    result = least_frequent_class(problems)

    assert isinstance(result, str), "Return type must be str; got " + str(type(result))
    assert result == "nesting_outlier", "Must be the class name; got " + repr(result)


def test_single_distinct_class_returns_that_class() -> None:
    """All findings share one class -> that class returned (not None).

    Kills an impl that returns None unless >= 2 distinct classes exist.
    """
    problems = [_p("complexity_outlier", i) for i in range(3)]

    result = least_frequent_class(problems)

    assert result == "complexity_outlier", "Single-class list must return that class; got " + repr(
        result
    )
