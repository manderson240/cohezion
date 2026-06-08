"""Item 208: finding_ids_for_class() — all finding-ids for a given class (2026-06-08).

``finding_ids_for_class(problems: list[Problem], problem_class: str)``
-> ``list[str]``:
Returns ``[p.finding_id for p in problems if p.problem_class == problem_class]``
in input order.  Not found -> ``[]``.  Empty problems -> ``[]``.  Pure; no I/O.

The bulk ID-extraction face; complementary to :func:`problems_for_finding_id`
(which goes ID -> Problem) and :func:`finding_ids` (item 189: all IDs)::

    ids = finding_ids_for_class(findings, "complexity_outlier")
    # ["complexity_outlier:src/foo.py", ...]

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns list of finding_id strings, not Problem objects.
     Kills an impl that returns the Problem instances instead of their ids.
  2. Filters to the requested class only (other classes excluded).
     Kills an impl that returns all finding_ids from all classes.
  3. Preserves input order.
     Kills an impl that returns ids in alphabetical or arbitrary order.
  4. Class absent -> [] (not raises).
     Kills an impl that raises KeyError on miss.
  5. Empty problems -> [] (not raises).
     Kills an impl that raises IndexError on empty input.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    finding_ids_for_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_strings_not_problem_objects() -> None:
    """Returns list[str] of finding_ids, not list[Problem].

    PRIMARY DISCRIMINATOR: kills an impl that returns Problem instances
    instead of extracting their finding_id strings.
    """
    p = _p("complexity_outlier", 7)
    problems = [p]

    result = finding_ids_for_class(problems, "complexity_outlier")

    assert len(result) == 1, "one match expected; got " + repr(result)
    assert isinstance(result[0], str), "elements must be str (finding_ids); got " + repr(
        type(result[0])
    )
    assert result[0] == "complexity_outlier:7", "must return the finding_id string; got " + repr(
        result[0]
    )


def test_filters_to_requested_class_only() -> None:
    """Only finding_ids for the requested class are returned.

    Kills an impl that returns all finding_ids regardless of class.
    """
    problems = [
        _p("complexity_outlier", 0),
        _p("nesting_outlier", 0),
        _p("complexity_outlier", 1),
    ]

    result = finding_ids_for_class(problems, "complexity_outlier")

    assert result == ["complexity_outlier:0", "complexity_outlier:1"], (
        "only complexity_outlier ids in order; got " + repr(result)
    )
    assert "nesting_outlier:0" not in result, "other class ids must be excluded; got " + repr(
        result
    )


def test_preserves_input_order() -> None:
    """Results are in the same order they appear in problems.

    Kills an impl that returns ids in alphabetical or sorted order.
    Indices 2, 0, 1 are in that order -> result must follow that order.
    """
    problems = [
        _p("complexity_outlier", 2),
        _p("nesting_outlier"),
        _p("complexity_outlier", 0),
        _p("complexity_outlier", 1),
    ]

    result = finding_ids_for_class(problems, "complexity_outlier")

    assert result == ["complexity_outlier:2", "complexity_outlier:0", "complexity_outlier:1"], (
        "must preserve input order (2, 0, 1); got " + repr(result)
    )


def test_class_absent_returns_empty_list() -> None:
    """Class not in problems -> [] (not raises).

    Kills an impl that raises KeyError on miss.
    """
    problems = [_p("complexity_outlier"), _p("nesting_outlier")]

    result = finding_ids_for_class(problems, "long_function")

    assert result == [], "absent class must return []; got " + repr(result)


def test_empty_problems_returns_empty_list() -> None:
    """Empty problems -> [] (not raises).

    Kills an impl that raises IndexError on empty input.
    """
    result = finding_ids_for_class([], "complexity_outlier")

    assert result == [], "empty input must return []; got " + repr(result)
