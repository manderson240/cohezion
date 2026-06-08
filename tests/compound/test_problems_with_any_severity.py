"""Item 380: problems_with_any_severity() -- labelled-only filter (2026-06-08).

``problems_with_any_severity(problems) -> list[Problem]``:
Returns all Problem objects whose severity field is a non-empty string.
Complement of problems_without_severity.  Order preserved.
Empty input -> [].  All unlabelled -> [].  Pure; no I/O.

Discriminating tests:

  1. PRIMARY DISC.: keeps LABELLED only (severity != '').
     Kills impl returning ALL problems (or the unlabelled subset).
  2. Complement: result union problems_without_severity == original list.
     Kills impl that drops some labelled problems.
  3. Order preserved.
     Kills impl that sorts or reorders.
  4. Empty input returns [].
     Kills impl raising on empty.
  5. Returns Problem objects, not severity strings.
     Kills impl returning [p.severity for p in ...].
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_with_any_severity,
    problems_without_severity,
)


def _p(cls: str, fid: str, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_keeps_labelled_only_not_all() -> None:
    """Keeps Problems with non-empty severity; unlabelled excluded.

    PRIMARY DISCRIMINATOR: kills impl returning all problems.
    """
    problems = [
        _p("sec", "CVE-001", "HIGH"),
        _p("style", "STY-001"),  # unlabelled
        _p("perf", "PERF-001", "LOW"),
    ]
    result = problems_with_any_severity(problems)
    assert len(result) == 2, "HIGH + LOW = 2 labelled; got " + repr(len(result))
    assert all(p.severity != "" for p in result), "All results must have non-empty severity"
    assert all(isinstance(p, Problem) for p in result), "Must return Problem objects"


def test_complement_partition() -> None:
    """labelled + unlabelled == original list (partition invariant).

    Kills impl that drops some labelled problems.
    """
    problems = [
        _p("a", "f:0", "HIGH"),
        _p("b", "f:1"),
        _p("c", "f:2", "MEDIUM"),
        _p("d", "f:3"),
    ]
    labelled = problems_with_any_severity(problems)
    unlabelled = problems_without_severity(problems)
    assert len(labelled) + len(unlabelled) == len(problems), (
        "Partition must cover all problems; labelled="
        + repr(len(labelled))
        + " unlabelled="
        + repr(len(unlabelled))
    )


def test_order_preserved() -> None:
    """Problems are returned in original insertion order."""
    problems = [
        _p("c", "f:0", "HIGH"),
        _p("a", "f:1", "LOW"),
        _p("b", "f:2", "MEDIUM"),
    ]
    result = problems_with_any_severity(problems)
    assert [p.finding_id for p in result] == ["f:0", "f:1", "f:2"], "Order preserved; got " + repr(
        [p.finding_id for p in result]
    )


def test_empty_returns_empty() -> None:
    """Empty input returns [] without raising."""
    assert problems_with_any_severity([]) == []


def test_all_unlabelled_returns_empty() -> None:
    """All unlabelled problems -> [] (none pass the filter)."""
    problems = [_p("a", "f:0"), _p("b", "f:1"), _p("c", "f:2")]
    result = problems_with_any_severity(problems)
    assert result == [], "All unlabelled -> []; got " + repr(result)
