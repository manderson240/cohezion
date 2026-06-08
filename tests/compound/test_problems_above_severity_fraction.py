"""Item 251: problems_above_severity_fraction() — fraction-gated severity alerting (2026-06-08).

``problems_above_severity_fraction(problems, severity, min_fraction) -> list[Problem]``:
Returns ``filter_problems_by_severity(problems, severity)`` when
``severity_fraction(problems, severity) > min_fraction``, otherwise ``[]``.
Useful for suppressing severity noise: only surface critical problems when
they represent a meaningful fraction of the total labelled scan.
Input order is preserved among returned problems.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns the list only when fraction STRICTLY EXCEEDS
     min_fraction (> not ≥).  Kills impl using ≥ that returns the list when
     fraction equals the threshold.
  2. Returns [] when severity fraction is below min_fraction.
     Kills impl that always returns all problems at the severity.
  3. Returns [] when there are no labelled problems (division guard).
     Kills impl that raises ZeroDivisionError.
  4. Input order preserved among returned problems.
     Kills impl that sorts the output.
  5. Return type is list[Problem], not a frozenset or dict.
     Kills impl returning a count or frozenset.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_above_severity_fraction,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_list_returned_only_when_fraction_strictly_exceeds_threshold() -> None:
    """Returns the list when fraction > min_fraction, [] when fraction == min_fraction.

    PRIMARY DISCRIMINATOR: kills impl using ≥ instead of >.
    3 HIGH / 3 labelled = fraction 1.0.  min_fraction=1.0 → [] (not strictly >).
    min_fraction=0.99 → returns the 3 HIGH problems.
    """
    problems = [
        _ps("alpha", 0, "HIGH"), _ps("alpha", 1, "HIGH"), _ps("alpha", 2, "HIGH"),
    ]
    # Exactly at threshold → must return []
    result_at = problems_above_severity_fraction(problems, "HIGH", 1.0)
    assert result_at == [], (
        "fraction=1.0 == min_fraction=1.0 → [] (strictly >); got " + repr(result_at)
    )
    # Just above threshold → must return the problems
    result_above = problems_above_severity_fraction(problems, "HIGH", 0.99)
    assert len(result_above) == 3, (
        "fraction=1.0 > min_fraction=0.99 → 3 problems; got " + repr(result_above)
    )


def test_empty_list_when_fraction_below_threshold() -> None:
    """Returns [] when the severity fraction is below min_fraction.

    Kills impl that always returns all problems at the severity.
    1 HIGH / 4 labelled = 0.25.  min_fraction=0.5 → [].
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "LOW"), _ps("alpha", 2, "LOW"), _ps("alpha", 3, "LOW"),
    ]
    result = problems_above_severity_fraction(problems, "HIGH", 0.5)
    assert result == [], "fraction=0.25 ≤ min_fraction=0.5 → []; got " + repr(result)


def test_empty_list_when_no_labelled_problems() -> None:
    """Returns [] when no problem has a non-empty severity.

    Kills impl that raises ZeroDivisionError when all severities are ''.
    """
    problems = [
        Problem(problem_class="alpha", finding_id="alpha:0"),
        Problem(problem_class="beta",  finding_id="beta:0"),
    ]
    result = problems_above_severity_fraction(problems, "HIGH", 0.1)
    assert result == [], "No labelled problems → fraction=0.0 ≤ any threshold → []; got " + repr(result)


def test_input_order_preserved() -> None:
    """Returned problems are in the same order as the input.

    Kills impl that sorts the output.
    """
    p_z = Problem(problem_class="alpha", finding_id="alpha:z", severity="HIGH")
    p_a = Problem(problem_class="alpha", finding_id="alpha:a", severity="HIGH")
    p_m = Problem(problem_class="alpha", finding_id="alpha:m", severity="HIGH")
    result = problems_above_severity_fraction([p_z, p_a, p_m], "HIGH", 0.0)
    assert [p.finding_id for p in result] == ["alpha:z", "alpha:a", "alpha:m"], (
        "Input order must be preserved; got " + repr([p.finding_id for p in result])
    )


def test_return_type_is_list_of_problems() -> None:
    """Return type is list[Problem], not frozenset or count.

    Kills impl returning a frozenset of finding_ids or an int count.
    """
    problems = [_ps("alpha", 0, "CRITICAL")]
    result = problems_above_severity_fraction(problems, "CRITICAL", 0.0)
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert len(result) == 1
    assert isinstance(result[0], Problem), "Elements must be Problem"
