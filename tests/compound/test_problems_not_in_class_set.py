"""Item 213: problems_not_in_class_set() — exclude-list filter (2026-06-08).

``problems_not_in_class_set(problems: list[Problem], exclude: set[str])``
-> ``list[Problem]``:
Returns Problems whose ``problem_class`` is NOT in *exclude*.
Empty *exclude* -> full list (nothing excluded).
Empty *problems* -> [].  Preserves input order.  Pure; no I/O.

Inverse of ``filter_by_class`` (item 192 — keep listed classes);
this one REMOVES listed classes::

    rest = problems_not_in_class_set(findings, {"complexity_outlier"})

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: excluded class ABSENT from result.
     Kills an impl that returns only excluded-class Problems (the inverse).
  2. Empty exclude -> full list unchanged.
     Kills an impl that returns [] on empty exclude.
  3. Non-excluded class in result.
     Kills an impl that excludes all classes.
  4. Empty problems -> [] (not raises).
     Kills an impl that raises on empty input.
  5. Preserves input order for non-excluded items.
     Kills an impl that re-sorts the output.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_not_in_class_set,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_excluded_class_absent_from_result() -> None:
    """Excluded class not in result.

    PRIMARY DISCRIMINATOR: kills an impl that returns ONLY excluded-class
    Problems instead of excluding them.
    """
    problems = [
        _p("complexity_outlier"),
        _p("nesting_outlier"),
        _p("complexity_outlier", 1),
    ]
    exclude = {"complexity_outlier"}

    result = problems_not_in_class_set(problems, exclude)

    classes = {p.problem_class for p in result}
    assert "complexity_outlier" not in classes, "excluded class must be absent; got " + repr(
        classes
    )
    assert "nesting_outlier" in classes, "non-excluded class must be present; got " + repr(classes)


def test_empty_exclude_returns_full_list() -> None:
    """Empty exclude set -> all problems returned unchanged.

    Kills an impl that returns [] on empty exclude.
    """
    problems = [_p("complexity_outlier"), _p("nesting_outlier")]

    result = problems_not_in_class_set(problems, set())

    assert len(result) == 2, "empty exclude must return all problems; got " + repr(result)
    assert result[0] is problems[0]
    assert result[1] is problems[1]


def test_non_excluded_class_in_result() -> None:
    """Class not in exclude set -> present in result.

    Kills an impl that excludes all classes.
    """
    problems = [_p("long_function")]
    exclude = {"complexity_outlier", "nesting_outlier"}  # long_function not excluded

    result = problems_not_in_class_set(problems, exclude)

    assert len(result) == 1, "non-excluded class must be in result; got " + repr(result)
    assert result[0].problem_class == "long_function"


def test_empty_problems_returns_empty() -> None:
    """Empty problems -> [] (not raises).

    Kills an impl that raises IndexError on empty input.
    """
    result = problems_not_in_class_set([], {"complexity_outlier"})

    assert result == [], "empty input must return []; got " + repr(result)


def test_preserves_input_order() -> None:
    """Non-excluded items appear in the same order as in problems.

    Kills an impl that re-sorts by class name or reverses.
    """
    problems = [
        _p("nesting_outlier", 2),
        _p("long_function", 0),
        _p("nesting_outlier", 0),
    ]
    exclude = {"complexity_outlier"}  # none of the above excluded

    result = problems_not_in_class_set(problems, exclude)

    assert len(result) == 3, "all 3 must be present; got " + repr(len(result))
    assert result[0].finding_id == "nesting_outlier:2", (
        "first element must preserve order; got " + repr(result[0].finding_id)
    )
    assert result[1].finding_id == "long_function:0"
    assert result[2].finding_id == "nesting_outlier:0"
