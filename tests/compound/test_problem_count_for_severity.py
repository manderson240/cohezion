"""Item 397: problem_count_for_severity() — record count for a specific severity (2026-06-08).

``problem_count_for_severity(problems, target_severity) -> int``:
Returns the total number of Problem records where severity == target_severity.
'' is a valid target for counting unlabelled records.
Returns 0 when the severity is absent or problems is empty.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: '' as target counts unlabelled records (not filtered out).
     Kills impl that skips unlabelled records before counting.
  2. Returns an INTEGER count, not a list or None.
     Kills impl returning matching Problem objects.
  3. Returns 0 when target severity is absent (not KeyError or None).
     Kills impl raising or returning None on miss.
  4. Empty problems -> 0.
     Kills impl raising on empty.
  5. Only counts the specified severity, not all problems.
     Kills impl returning len(problems).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problem_count_for_severity,
)


def _p(sev: str, fid: str = "f", cls: str = "cls") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_empty_string_target_counts_unlabelled() -> None:
    """'' as target_severity counts unlabelled records.

    PRIMARY DISCRIMINATOR: kills impl filtering out unlabelled records.
    """
    problems = [_p("HIGH"), _p(""), _p(""), _p("LOW")]
    result = problem_count_for_severity(problems, "")
    assert isinstance(result, int), "Must return int; got " + repr(type(result))
    assert result == 2, "2 unlabelled records; got " + repr(result)


def test_returns_integer_not_list() -> None:
    """Returns an integer, not a list of Problem objects.

    Kills impl returning matching Problem objects.
    """
    problems = [_p("HIGH"), _p("HIGH"), _p("LOW")]
    result = problem_count_for_severity(problems, "HIGH")
    assert isinstance(result, int), "Must return int; got " + repr(type(result))
    assert result == 2, "HIGH has 2 records; got " + repr(result)


def test_returns_zero_when_severity_absent() -> None:
    """Returns 0 when target severity is absent, not None or KeyError.

    Kills impl raising or returning None on miss.
    """
    problems = [_p("HIGH"), _p("LOW")]
    result = problem_count_for_severity(problems, "CRITICAL")
    assert result == 0, "CRITICAL absent -> 0; got " + repr(result)
    assert isinstance(result, int)


def test_empty_problems_returns_zero() -> None:
    """Empty problems list returns 0."""
    assert problem_count_for_severity([], "HIGH") == 0


def test_counts_only_specified_severity() -> None:
    """Only the target severity is counted, not all problems.

    Kills impl returning len(problems).
    """
    problems = [_p("HIGH"), _p("LOW"), _p("CRITICAL"), _p("HIGH")]
    result = problem_count_for_severity(problems, "HIGH")
    assert result == 2, "HIGH appears twice; total=4; got " + repr(result)
    assert result != len(problems), "Must NOT return len(problems)"
