"""Item 277: problems_at_severity() — all problems with exact severity across all classes (2026-06-08).

``problems_at_severity(problems: list[Problem], severity: str) -> list[Problem]``:
Returns all problems whose severity exactly equals *severity* (case-sensitive),
preserving input order.  Empty input or absent severity → [].  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: filters to EXACT severity string (case-sensitive).
     Kills impl doing case-insensitive match (e.g. "HIGH" == "high").
  2. Cross-class: returns problems from ALL classes, not just the first.
     Kills impl that stops after finding a matching class.
  3. severity="" returns unlabelled problems only (not all non-empty).
     Kills impl returning all problems with any non-empty severity when
     severity="" is passed (i.e. `if p.severity` instead of `== severity`).
  4. Preserves input order.
     Kills impl that sorts or de-duplicates the output.
  5. Returns list[Problem] not a count.
     Kills impl returning int or frozenset.
"""
from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_at_severity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_exact_case_sensitive_match() -> None:
    """Filter is exact and case-sensitive.

    PRIMARY DISCRIMINATOR: kills impl doing case-insensitive match.
    Input has 'HIGH', 'high', 'High'. Only 'HIGH' must match severity='HIGH'.
    """
    problems = [
        _p("alpha", 0, "HIGH"),
        _p("alpha", 1, "high"),
        _p("alpha", 2, "High"),
        _p("alpha", 3, "LOW"),
    ]
    result = problems_at_severity(problems, "HIGH")
    assert len(result) == 1, (
        "Only 'HIGH' (exact) must match; got " + repr([p.finding_id for p in result])
    )
    assert result[0].finding_id == "alpha:0"


def test_returns_problems_from_all_classes() -> None:
    """Returns matching problems from ALL classes, not just the first.

    Kills impl that stops after finding a matching class.
    """
    problems = [
        _p("alpha", 0, "HIGH"),
        _p("beta", 0, "LOW"),
        _p("gamma", 0, "HIGH"),
    ]
    result = problems_at_severity(problems, "HIGH")
    finding_ids = [p.finding_id for p in result]
    assert "alpha:0" in finding_ids, "alpha:HIGH must be included"
    assert "gamma:0" in finding_ids, "gamma:HIGH must be included"
    assert "beta:0" not in finding_ids, "beta:LOW must not be included"


def test_empty_severity_returns_unlabelled_only() -> None:
    """severity='' returns unlabelled problems only.

    Kills impl returning all problems when severity='' is passed
    (i.e. using `if p.severity` which excludes '' rather than ==).
    """
    problems = [
        _p("alpha", 0),               # severity=""
        _p("alpha", 1, "HIGH"),
        _p("beta", 0),                 # severity=""
    ]
    result = problems_at_severity(problems, "")
    finding_ids = {p.finding_id for p in result}
    assert "alpha:0" in finding_ids, "Unlabelled alpha:0 must be returned"
    assert "beta:0" in finding_ids, "Unlabelled beta:0 must be returned"
    assert "alpha:1" not in finding_ids, "HIGH-labelled alpha:1 must not be returned"


def test_preserves_input_order() -> None:
    """Output preserves the original input order.

    Kills impl that sorts or reorders the output.
    """
    problems = [
        _p("beta", 0, "HIGH"),
        _p("alpha", 0, "HIGH"),
        _p("gamma", 0, "HIGH"),
    ]
    result = problems_at_severity(problems, "HIGH")
    assert [p.finding_id for p in result] == ["beta:0", "alpha:0", "gamma:0"], (
        "Order must be preserved; got " + repr([p.finding_id for p in result])
    )


def test_returns_list_of_problems() -> None:
    """Return type is list[Problem], not int or frozenset.

    Kills impl returning a count or set.
    """
    problems = [_p("alpha", 0, "HIGH"), _p("alpha", 1, "LOW")]
    result = problems_at_severity(problems, "HIGH")
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert all(isinstance(p, Problem) for p in result), "List must contain Problem instances"
