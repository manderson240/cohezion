"""Item 199: class_finding_count() — per-class scalar count (2026-06-08).

``class_finding_count(problems: list[Problem], problem_class: str)``
→ ``int``:
Returns the number of findings in *problems* whose ``problem_class``
equals *problem_class*.  Class absent → ``0``.  Empty list → ``0``.
Pure; no I/O.

Avoids building a full frequency dict when only one class count is needed::

    assert class_finding_count(findings, "complexity_outlier") == 0

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: class present -> correct count returned (not 0 or 1).
     Kills an impl that always returns 0 or always returns 1.
  2. Class absent -> 0 (not None, not raises).
     Kills an impl that raises KeyError or returns None on miss.
  3. Empty list -> 0 (no raises).
     Kills an impl that raises IndexError on empty input.
  4. Only matching findings counted (other classes not included).
     Kills an impl that returns len(problems) instead of per-class count.
  5. Return type is int.
     Kills an impl that returns a float or a Problem.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_finding_count,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_class_present_returns_correct_count() -> None:
    """Class present multiple times -> correct count returned.

    PRIMARY DISCRIMINATOR: kills an impl that always returns 0 (empty
    always) or always returns 1 (presence check only, not frequency).
    """
    problems = [
        _p("complexity_outlier", 0),
        _p("nesting_outlier"),
        _p("complexity_outlier", 1),
        _p("complexity_outlier", 2),
    ]  # complexity_outlier: 3

    result = class_finding_count(problems, "complexity_outlier")

    assert result == 3, "Count must be 3; got " + repr(result)


def test_class_absent_returns_zero() -> None:
    """Class not in problems -> 0 (not None, not raises).

    Kills an impl that raises KeyError or returns None on miss.
    """
    problems = [_p("complexity_outlier"), _p("nesting_outlier")]

    result = class_finding_count(problems, "long_function")

    assert result == 0, "Absent class must return 0; got " + repr(result)


def test_empty_list_returns_zero() -> None:
    """Empty problems list -> 0 (no raises).

    Kills an impl that raises IndexError on empty input.
    """
    result = class_finding_count([], "complexity_outlier")

    assert result == 0, "Empty input must return 0; got " + repr(result)


def test_only_matching_class_counted() -> None:
    """Count is per-class only; other classes not included.

    Kills an impl that returns len(problems) (total count) instead of the
    per-class count, ignoring the problem_class filter.
    """
    problems = [_p("complexity_outlier"), _p("nesting_outlier"), _p("long_function")]

    result = class_finding_count(problems, "nesting_outlier")

    assert result == 1, "Only nesting_outlier counted (not all 3); got " + repr(result)


def test_return_type_is_int() -> None:
    """Return value is an int.

    Kills an impl that returns float, Problem, or list.
    """
    problems = [_p("complexity_outlier"), _p("complexity_outlier", 1)]

    result = class_finding_count(problems, "complexity_outlier")

    assert isinstance(result, int), "Return type must be int; got " + str(type(result))
    assert result == 2
