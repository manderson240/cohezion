"""Item 395: problems_by_severity() — group Problem records by severity (2026-06-08).

``problems_by_severity(problems) -> dict[str, list[Problem]]``:
Returns {severity: [Problem, ...]} for every distinct severity string.
'' (empty string) is a valid key for unlabelled records.
Preserves input order within each list.
Empty -> {}.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: values are LIST[Problem] objects, not counts.
     Kills impl returning severity_histogram counts.
  2. '' is included as a key when unlabelled problems exist.
     Kills impl that filters out unlabelled records.
  3. Input order preserved within each severity list.
     Kills impl that sorts records within a bucket.
  4. Empty input returns {}.
     Kills impl raising on empty.
  5. Total record count across all lists equals len(problems).
     Kills impl double-counting or dropping records.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_by_severity,
)


def _p(sev: str, fid: str = "f", cls: str = "cls") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_values_are_lists_of_problem_objects() -> None:
    """Values are list[Problem], not counts.

    PRIMARY DISCRIMINATOR: kills impl returning severity_histogram.
    """
    p0 = _p("HIGH", "f:0")
    p1 = _p("HIGH", "f:1")
    p2 = _p("LOW", "f:2")
    result = problems_by_severity([p0, p1, p2])
    assert isinstance(result, dict)
    assert isinstance(result["HIGH"], list), "Value must be list"
    assert all(isinstance(p, Problem) for p in result["HIGH"])
    assert len(result["HIGH"]) == 2
    assert len(result["LOW"]) == 1


def test_empty_string_key_for_unlabelled_problems() -> None:
    """'' is a valid key when unlabelled records exist.

    Kills impl filtering out unlabelled problems.
    """
    p0 = _p("HIGH", "f:0")
    p1 = _p("", "f:1")  # unlabelled
    p2 = _p("", "f:2")  # unlabelled
    result = problems_by_severity([p0, p1, p2])
    assert "" in result, "'' must be a key for unlabelled records"
    assert len(result[""]) == 2, "Two unlabelled records; got " + repr(len(result[""]))


def test_input_order_preserved_within_severity() -> None:
    """Input order is preserved within each severity bucket.

    Kills impl that re-sorts records inside a bucket.
    """
    p0 = _p("HIGH", "z-fid")
    p1 = _p("HIGH", "a-fid")
    result = problems_by_severity([p0, p1])
    assert result["HIGH"][0].finding_id == "z-fid"
    assert result["HIGH"][1].finding_id == "a-fid"


def test_empty_returns_empty_dict() -> None:
    """Empty input returns {}."""
    assert problems_by_severity([]) == {}


def test_total_records_equals_input_length() -> None:
    """Sum of all list lengths equals len(problems).

    Kills impl double-counting or dropping records.
    """
    problems = [_p("HIGH"), _p("LOW"), _p(""), _p("HIGH"), _p("CRITICAL")]
    result = problems_by_severity(problems)
    total = sum(len(v) for v in result.values())
    assert total == len(problems), "Total records = 5; got " + repr(total)
