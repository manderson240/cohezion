"""Item 309: most_severe_class() — class with highest-priority dominant severity (2026-06-08).

``most_severe_class(problems, severity_order) -> str | None``:
Given a caller-supplied severity ordering (list from most to least severe),
finds the class whose dominant severity ranks highest in that order.
Ties in rank broken by class name ascending.
Class whose dominant severity is absent from severity_order treated as worst rank.
No labelled classes -> None.  Pure; no I/O.

Uses dominant_severity_per_class as a building block.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: rank is position in severity_order, NOT alphabetical sort.
     Kills impl sorting alphabetically on severity string.
  2. Class absent from severity_order treated as worst rank (not error, not best).
     Kills impl raising or placing absent-severity class at top.
  3. Ties in rank broken by class name ascending.
     Kills impl with wrong tie-break direction.
  4. No labelled classes (all empty severity) -> None.
     Kills impl returning a class string when nothing is labelled.
  5. Return type is str | None; returned name is the actual class name.
     Kills impl returning the severity string instead of the class name.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    most_severe_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, sev: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{sev}:{idx}", severity=sev)


def _pu(cls: str, idx: int) -> Problem:
    """Unlabelled problem."""
    return Problem(problem_class=cls, finding_id=f"{cls}:u:{idx}")


SEV_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_rank_by_severity_order_not_alphabetical() -> None:
    """Rank is determined by position in severity_order, not alphabetical sort.

    PRIMARY DISCRIMINATOR: kills impl sorting by severity string alphabetically.
    alpha: dominant=HIGH (rank=1 in SEV_ORDER).
    beta: dominant=MEDIUM (rank=2 in SEV_ORDER).
    alpha wins because HIGH ranks higher than MEDIUM in SEV_ORDER.
    Alphabetically: HIGH < MEDIUM -> would return beta if sorted wrong.
    """
    problems = [
        _p("alpha", "HIGH", 0),
        _p("alpha", "HIGH", 1),
        _p("beta", "MEDIUM", 0),
        _p("beta", "MEDIUM", 1),
    ]
    result = most_severe_class(problems, SEV_ORDER)
    assert result == "alpha", (
        "alpha dominant=HIGH (rank=1) > beta dominant=MEDIUM (rank=2) -> alpha; got " + repr(result)
    )


def test_class_absent_from_severity_order_treated_as_worst_rank() -> None:
    """Class with dominant severity absent from severity_order gets worst rank.

    Kills impl raising or placing absent-severity class at top.
    alpha: dominant=UNKNOWN (not in SEV_ORDER) -> worst rank.
    beta: dominant=INFO (rank=4 in SEV_ORDER) -> better than UNKNOWN.
    beta wins.
    """
    problems = [
        _p("alpha", "UNKNOWN", 0),  # not in severity_order
        _p("beta", "INFO", 0),
    ]
    result = most_severe_class(problems, SEV_ORDER)
    assert result == "beta", (
        "alpha UNKNOWN absent -> worst rank; beta INFO -> rank=4; beta wins; got " + repr(result)
    )


def test_ties_in_rank_broken_by_class_name_ascending() -> None:
    """Equal rank ties broken by class name ascending (alphabetically first wins).

    Kills impl with wrong tie-break direction.
    alpha and beta both dominant=HIGH -> tie; alpha < beta -> alpha wins.
    """
    problems = [
        _p("beta", "HIGH", 0),
        _p("alpha", "HIGH", 0),
    ]
    result = most_severe_class(problems, SEV_ORDER)
    assert result == "alpha", (
        "alpha and beta both dominant=HIGH; alpha < beta -> alpha wins; got " + repr(result)
    )


def test_no_labelled_classes_returns_none() -> None:
    """No labelled classes (all empty severity) -> None.

    Kills impl returning a class name when no severity data exists.
    """
    problems = [_pu("alpha", 0), _pu("beta", 0)]
    result = most_severe_class(problems, SEV_ORDER)
    assert result is None, "no labelled classes -> None; got " + repr(result)


def test_returns_class_name_not_severity_string() -> None:
    """Return value is the class name string, not the severity string.

    Kills impl that returns the dominant severity instead of the class.
    """
    problems = [_p("my_class", "CRITICAL", 0)]
    result = most_severe_class(problems, SEV_ORDER)
    assert result == "my_class", (
        "Returns class name 'my_class', not severity 'CRITICAL'; got " + repr(result)
    )
