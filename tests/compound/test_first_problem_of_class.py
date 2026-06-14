"""Item 194: first_problem_of_class() — first-finding-per-class accessor (2026-06-08).

``first_problem_of_class(problems: list[Problem], problem_class: str)``
→ ``Problem | None``:
Returns the first finding whose ``problem_class`` equals *problem_class*, or
``None`` if no such finding exists.  Empty list → ``None``.  Pure; no I/O.

Enables walrus-operator idioms without a manual ``next(iter(...), None)``::

    if p := first_problem_of_class(findings, "complexity_outlier"):
        report(p.finding_id)

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: class present → first matching Problem returned (not last, not None).
     Kills an impl that returns None, or the last match, or raises.
  2. Class absent → None.
     Kills an impl that returns a placeholder Problem on miss.
  3. Empty list → None (no raises).
     Kills an impl that raises IndexError on empty input.
  4. Returns the FIRST match when multiple exist (not last, not arbitrary).
     Kills an impl that returns the last matching finding.
  5. Return value is a Problem instance, not a string.
     Kills an impl that returns the finding_id string instead of the Problem.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    first_problem_of_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_class_present_returns_first_match() -> None:
    """Class present → first matching Problem returned.

    PRIMARY DISCRIMINATOR: kills an impl that returns None on hit, or
    returns something other than the first matching Problem.
    """
    problems = [
        _p("nesting_outlier"),
        _p("complexity_outlier", 0),
        _p("complexity_outlier", 1),
    ]

    result = first_problem_of_class(problems, "complexity_outlier")

    assert result is not None, "Must return a Problem on hit, not None"
    assert result.finding_id == "complexity_outlier:0", (
        f"Must return FIRST match; got {result.finding_id!r}"
    )


def test_class_absent_returns_none() -> None:
    """Class not in problems → None.

    Kills an impl that returns a placeholder Problem or raises KeyError on miss.
    """
    problems = [_p("complexity_outlier"), _p("nesting_outlier")]

    result = first_problem_of_class(problems, "long_function")

    assert result is None, f"Absent class must return None; got {result!r}"


def test_empty_list_returns_none() -> None:
    """Empty list → None (no raises).

    Kills an impl that raises IndexError on empty input.
    """
    result = first_problem_of_class([], "complexity_outlier")

    assert result is None, f"Empty list must return None; got {result!r}"


def test_returns_first_not_last_when_multiple_exist() -> None:
    """Multiple matches → first match returned, not the last.

    Kills an impl that returns the last matching finding (e.g. by iterating
    and overwriting a variable instead of returning on first hit).
    """
    problems = [
        _p("complexity_outlier", 99),
        _p("complexity_outlier", 0),
        _p("complexity_outlier", 1),
    ]

    result = first_problem_of_class(problems, "complexity_outlier")

    assert result is not None
    assert result.finding_id == "complexity_outlier:99", (
        f"Must return first match (idx=99); got {result.finding_id!r}"
    )


def test_return_value_is_problem_instance() -> None:
    """Return value is a Problem instance, not a string or other type.

    Kills an impl that returns the finding_id string instead of the
    full Problem object.
    """
    problems = [_p("long_function", 3)]

    result = first_problem_of_class(problems, "long_function")

    assert isinstance(result, Problem), f"Return type must be Problem; got {type(result)}"
    assert result.finding_id == "long_function:3", (
        f"Problem must have correct finding_id; got {result.finding_id!r}"
    )
