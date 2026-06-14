"""Item 399: has_problems_for_severity() — boolean presence check for a severity (2026-06-08).

``has_problems_for_severity(problems, target_severity) -> bool``:
Returns True if at least one Problem record has severity == target_severity.
'' is a valid target for testing if any unlabelled records exist.
Returns False when absent or problems is empty.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: '' as target returns True when unlabelled records exist.
     Kills impl that filters out unlabelled records before checking.
  2. Returns a BOOL (type is bool, not int 0/1).
     Kills impl returning problem_count_for_severity.
  3. Returns False (not 0, not None) when severity is absent.
     Kills impl returning the count.
  4. Empty problems -> False.
     Kills impl raising on empty.
  5. Returns False when no record matches target (others present).
     Kills impl returning True for any non-empty input.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    has_problems_for_severity,
)


def _p(sev: str, fid: str = "f") -> Problem:
    return Problem(problem_class="cls", finding_id=fid, severity=sev)


def test_empty_string_target_true_when_unlabelled_exist() -> None:
    """'' as target returns True when unlabelled records exist.

    PRIMARY DISCRIMINATOR: kills impl filtering out unlabelled records.
    """
    problems = [_p("HIGH"), _p(""), _p("LOW")]
    result = has_problems_for_severity(problems, "")
    assert type(result) is bool, "Must return bool; got " + repr(type(result))
    assert result is True, "Unlabelled records present -> True; got " + repr(result)


def test_returns_bool_not_int() -> None:
    """Returns bool, not int.

    Kills impl returning problem_count_for_severity.
    """
    result = has_problems_for_severity([_p("HIGH"), _p("HIGH")], "HIGH")
    assert type(result) is bool, "Must return bool; got " + repr(type(result))
    assert result is True


def test_false_is_bool_not_zero_when_absent() -> None:
    """Returns False (bool), not 0 (int) when severity is absent."""
    result = has_problems_for_severity([_p("HIGH")], "CRITICAL")
    assert type(result) is bool, "Must return bool; got " + repr(type(result))
    assert result is False


def test_empty_problems_returns_false() -> None:
    """Empty problems list returns False."""
    assert has_problems_for_severity([], "HIGH") is False


def test_false_when_no_record_matches_severity() -> None:
    """Returns False when no record has the target severity.

    Kills impl returning True for any non-empty input.
    """
    problems = [_p("HIGH"), _p("LOW"), _p("MEDIUM")]
    assert has_problems_for_severity(problems, "CRITICAL") is False
