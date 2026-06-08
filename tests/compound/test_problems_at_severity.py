"""Item 277: problems_at_severity() — all problems with a given severity (2026-06-08).

``problems_at_severity(problems: list[Problem], severity: str) -> list[Problem]``:
Returns all Problem instances in problems where p.severity == severity (exact,
case-sensitive). Preserves input order. Empty input or absent severity -> [].
severity="" returns only unlabelled problems. Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: match is EXACT and CASE-SENSITIVE ("HIGH" \!= "high").
     Kills impl doing case-insensitive comparison.
  2. Preserves input order among returned problems.
     Kills impl that sorts or reverses the result.
  3. Empty input -> [] without raising.
     Kills impl that raises on empty input.
  4. severity="" returns ONLY unlabelled problems (not all problems).
     Kills impl treating severity="" as "no filter applied".
  5. Return type is list[Problem], not a count.
     Kills impl returning int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_at_severity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_match_is_case_sensitive() -> None:
    """Match is EXACT and CASE-SENSITIVE: 'HIGH' \!= 'high'.

    PRIMARY DISCRIMINATOR: kills impl doing case-insensitive comparison.
    """
    problems = [_ps("alpha", 0, "HIGH"), _ps("alpha", 1, "high")]
    result = problems_at_severity(problems, "HIGH")
    assert len(result) == 1, "Only 'HIGH' (uppercase) matches; got " + str(len(result))
    assert result[0].finding_id == "alpha:0", (
        "Matched wrong problem; got " + repr(result[0].finding_id)
    )


def test_preserves_input_order() -> None:
    """Result preserves the same order as the input list.

    Kills impl that sorts or reverses the result.
    """
    problems = [
        _ps("gamma", 2, "HIGH"),
        _ps("alpha", 0, "HIGH"),
        _ps("beta", 1, "HIGH"),
    ]
    result = problems_at_severity(problems, "HIGH")
    ids = [p.finding_id for p in result]
    assert ids == ["gamma:2", "alpha:0", "beta:1"], (
        "Order must match input; got " + repr(ids)
    )


def test_empty_input_returns_empty_list() -> None:
    """Empty input -> [] without raising.

    Kills impl that raises on empty input.
    """
    result = problems_at_severity([], "HIGH")
    assert result == [], "Empty input -> []; got " + repr(result)


def test_empty_severity_returns_only_unlabelled() -> None:
    """severity='' returns ONLY unlabelled problems, not all problems.

    Kills impl treating severity='' as 'return all'.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _p("beta", 1),          # severity="" (unlabelled)
        _ps("gamma", 2, "LOW"),
        _p("delta", 3),         # severity="" (unlabelled)
    ]
    result = problems_at_severity(problems, "")
    assert len(result) == 2, "Only 2 unlabelled problems; got " + str(len(result))
    assert all(p.severity == "" for p in result), "All returned must be unlabelled"


def test_return_type_is_list_of_problems() -> None:
    """Return type is list[Problem], not int or frozenset.

    Kills impl returning a count.
    """
    problems = [_ps("alpha", 0, "HIGH")]
    result = problems_at_severity(problems, "HIGH")
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert all(isinstance(p, Problem) for p in result), "Elements must be Problem instances"
