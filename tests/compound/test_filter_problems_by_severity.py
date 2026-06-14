"""Item 247: filter_problems_by_severity() — Problem list filtered by severity (2026-06-08).

``filter_problems_by_severity(problems: list[Problem], severity: str)``
-> ``list[Problem]``:
Returns all Problem instances where ``problem.severity == severity``
(exact, case-sensitive match).  Preserves input order.
Empty input → [].  Pure; no I/O.

Distinct from ``classes_with_max_severity()`` (returns class names);
this returns the actual Problem instances.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: only problems AT the target severity returned, not all.
     Kills an impl that returns all problems regardless of severity.
  2. Match is case-sensitive: "HIGH" ≠ "high".
     Kills an impl that lowercases before comparing.
  3. Input order preserved among returned problems.
     Kills an impl that sorts the output.
  4. Empty input → [].
     Kills an impl that raises or returns None.
  5. Return type is list[Problem] not frozenset or list of class names.
     Kills an impl returning class names like classes_with_max_severity().
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    filter_problems_by_severity,
)


def _p(cls: str, severity: str = "", idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=severity)


def test_only_problems_at_target_severity_returned() -> None:
    """Only problems with the target severity are returned.

    PRIMARY DISCRIMINATOR: kills impl returning all problems.
    p0 is HIGH, p1 is LOW.  Filter for HIGH → only p0 returned.
    """
    p0 = _p("alpha", "HIGH", 0)
    p1 = _p("alpha", "LOW", 1)

    result = filter_problems_by_severity([p0, p1], "HIGH")

    assert len(result) == 1, "Only p0 (HIGH) must be returned; got " + repr(result)
    assert result[0].finding_id == p0.finding_id


def test_case_sensitive_match() -> None:
    """Severity match is case-sensitive: 'HIGH' ≠ 'high'.

    Kills impl that lowercases before comparing.
    """
    p_upper = _p("alpha", "HIGH", 0)

    result = filter_problems_by_severity([p_upper], "high")

    assert result == [], "'high' must not match 'HIGH'; got " + repr(result)


def test_input_order_preserved() -> None:
    """Returned problems are in the same order as the input.

    Kills impl that sorts the output.
    """
    p_z = Problem(problem_class="alpha", finding_id="alpha:z", severity="HIGH")
    p_a = Problem(problem_class="alpha", finding_id="alpha:a", severity="HIGH")
    p_m = Problem(problem_class="alpha", finding_id="alpha:m", severity="HIGH")

    result = filter_problems_by_severity([p_z, p_a, p_m], "HIGH")

    assert len(result) == 3
    assert result[0].finding_id == "alpha:z", "First in input must be first out"
    assert result[1].finding_id == "alpha:a"
    assert result[2].finding_id == "alpha:m"


def test_empty_input_returns_empty_list() -> None:
    """Empty problems → [].

    Kills impl that raises or returns None.
    """
    result = filter_problems_by_severity([], "HIGH")
    assert result == [], "Empty input → []; got " + repr(result)


def test_return_type_is_list_of_problems() -> None:
    """Return type is list[Problem], not frozenset or list of strings.

    Kills impl returning class names like classes_with_max_severity().
    """
    p = _p("alpha", "CRITICAL")
    result = filter_problems_by_severity([p], "CRITICAL")

    assert isinstance(result, list), "Must return a list; got " + repr(type(result))
    assert len(result) == 1
    assert isinstance(result[0], Problem), "Elements must be Problem; got " + repr(type(result[0]))
