"""Item 195: problems_for_finding_id() — reverse lookup by ID (2026-06-08).

``problems_for_finding_id(problems: list[Problem], finding_id: str)``
→ ``list[Problem]``:
Returns all findings whose ``finding_id`` equals *finding_id*.
Not found → ``[]``.  Empty input → ``[]``.  Pure; no I/O.

The reverse direction of :func:`finding_ids` (Problem → ID); this goes
ID → Problem.  Usually returns 0 or 1 elements; returns multiple when
the same ID appears more than once.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: ID present → list containing that Problem (not None, not []).
     Kills an impl that always returns [] or raises on hit.
  2. ID absent → [] (no raises).
     Kills an impl that raises KeyError or returns None on miss.
  3. Empty list → [] (no raises).
     Kills an impl that raises IndexError on empty input.
  4. Duplicate IDs → all matching Problems returned.
     Kills an impl that returns only the first match (stops early).
  5. Return type is list, not Optional[Problem].
     Kills an impl that returns a single Problem (not wrapped in a list).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_for_finding_id,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_id_present_returns_list_with_matching_problem() -> None:
    """ID present → [matching Problem] (not None, not empty list).

    PRIMARY DISCRIMINATOR: kills an impl that always returns [] on any
    input, or raises instead of returning the matching finding.
    """
    target = _p("complexity_outlier", 5)
    problems = [_p("nesting_outlier"), target, _p("long_function")]

    result = problems_for_finding_id(problems, "complexity_outlier:5")

    assert len(result) == 1, f"One match expected; got {len(result)}: {result!r}"
    assert result[0] is target, f"Returned Problem must be the matching instance; got {result[0]!r}"


def test_id_absent_returns_empty_list() -> None:
    """ID not in problems → [] (no raises).

    Kills an impl that raises KeyError or returns None on miss.
    """
    problems = [_p("complexity_outlier"), _p("nesting_outlier")]

    result = problems_for_finding_id(problems, "long_function:0")

    assert result == [], f"Absent ID must return []; got {result!r}"


def test_empty_list_returns_empty() -> None:
    """Empty problems → [] (no raises).

    Kills an impl that raises IndexError on empty input.
    """
    result = problems_for_finding_id([], "complexity_outlier:0")

    assert result == [], f"Empty input must return []; got {result!r}"


def test_duplicate_ids_all_returned() -> None:
    """Same finding_id on multiple Problems → all returned.

    Kills an impl that returns only the first match (stops at the first
    occurrence) and ignores subsequent duplicates.
    """
    p0 = Problem(problem_class="complexity_outlier", finding_id="dup:0")
    p1 = Problem(problem_class="nesting_outlier", finding_id="dup:0")  # same ID, diff class
    problems = [p0, _p("long_function"), p1]

    result = problems_for_finding_id(problems, "dup:0")

    assert len(result) == 2, (
        f"Both duplicate-ID findings must be returned; got {len(result)}: {result!r}"
    )
    returned_classes = {p.problem_class for p in result}
    assert returned_classes == {"complexity_outlier", "nesting_outlier"}, (
        f"Both classes must appear; got {returned_classes!r}"
    )


def test_return_type_is_list() -> None:
    """Return value is a list, not a single Problem or None.

    Kills an impl that returns Optional[Problem] (single value) rather
    than the list form that handles 0, 1, or multiple matches uniformly.
    """
    problems = [_p("nesting_outlier", 2)]

    result = problems_for_finding_id(problems, "nesting_outlier:2")

    assert isinstance(result, list), f"Return type must be list; got {type(result)}"
    assert len(result) == 1
