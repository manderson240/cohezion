"""Item 431: problems_with_severity() -- filter problems by severity (2026-06-08).

``problems_with_severity(problems, severity) -> list[Problem]``:
Returns problems where p.severity == severity (case-sensitive).
Empty -> [].  No match -> [].  Preserves order.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: filters on severity field (NOT problem_class or finding_id).
     Kills impl using the wrong field.
  2. Case-sensitive match -- "HIGH" != "high".
     Kills impl doing case-insensitive comparison.
  3. Preserves order of matching records.
     Kills impl that reorders or deduplicates.
  4. No-match severity -> [] (not raise).
     Kills impl raising KeyError or returning None.
  5. Empty input -> [] (not raise).
     Kills impl with unguarded access.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_with_severity,
)


def _p(cls: str, fid: str, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_filters_on_severity_field_not_class() -> None:
    """PRIMARY DISC.: filters on severity, not problem_class or finding_id.

    All problems have the same class 'BUG'. Only those with severity='HIGH'
    should be returned. Kills impl using p.problem_class or p.finding_id.
    """
    problems = [
        _p("BUG", "f1", "HIGH"),
        _p("BUG", "f2", "LOW"),
        _p("BUG", "f3", "HIGH"),
        _p("BUG", "f4", "MEDIUM"),
    ]
    result = problems_with_severity(problems, "HIGH")
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert len(result) == 2, "Two HIGH problems; got " + repr(len(result))
    assert all(p.severity == "HIGH" for p in result), "All returned must be HIGH"


def test_case_sensitive_match() -> None:
    """'HIGH' does NOT match 'high' -- case-sensitive."""
    problems = [_p("cls", "f1", "HIGH"), _p("cls", "f2", "high")]
    result = problems_with_severity(problems, "HIGH")
    assert len(result) == 1, "Only one 'HIGH' (case-sensitive); got " + repr(len(result))
    assert result[0].finding_id == "f1", "Should return 'HIGH' problem; got " + repr(result)


def test_preserves_order() -> None:
    """Matching problems are returned in their original list order."""
    problems = [
        _p("a", "first", "HIGH"),
        _p("b", "second", "LOW"),
        _p("c", "third", "HIGH"),
    ]
    result = problems_with_severity(problems, "HIGH")
    assert [p.finding_id for p in result] == ["first", "third"], (
        "Order must be preserved; got " + repr([p.finding_id for p in result])
    )


def test_no_matching_severity_returns_empty_list() -> None:
    """No matching severity -> [], not raise."""
    problems = [_p("cls", "f1", "LOW"), _p("cls", "f2", "MEDIUM")]
    result = problems_with_severity(problems, "CRITICAL")
    assert result == [], "No match -> []; got " + repr(result)


def test_empty_input_returns_empty_list() -> None:
    """Empty input returns [], not raise."""
    result = problems_with_severity([], "HIGH")
    assert result == [], "Empty -> []; got " + repr(result)
    assert isinstance(result, list)
