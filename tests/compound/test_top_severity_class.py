"""Item 329: top_severity_class() — class with highest count at most-severe rank (2026-06-08).

``top_severity_class(problems, severity_order) -> str | None``:
Given a caller-supplied severity_order, finds the class with the highest count at
the most severe level (severity_order[0]).  If no class has any problems at that
severity, falls through to severity_order[1], etc.
Ties broken by alphabetically ascending class name.
If no labelled problems exist, returns None.  Empty severity_order -> None.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns class with highest COUNT at MOST-SEVERE rank, not first class seen.
     Kills impl returning insertion-order class at any severity.
  2. Falls through to next severity rank when top severity absent.
     Kills impl returning None when top rank has no problems.
  3. Ties at the same rank broken by ascending class name.
     Kills impl with arbitrary or reverse tie-break.
  4. Empty severity_order -> None.
     Kills impl crashing on empty ordering.
  5. No labelled problems -> None.
     Kills impl returning '' or raising on all-unlabelled input.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    top_severity_class,
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


def test_returns_class_with_highest_count_at_most_severe_rank() -> None:
    """Returns class with most problems at the first severity rank.

    PRIMARY DISCRIMINATOR: kills insertion-order or any-severity impl.
    alpha: 1 CRITICAL. beta: 3 CRITICAL. severity_order=[CRITICAL, HIGH].
    beta has highest count at CRITICAL -> beta wins.
    """
    problems = [
        _ps("alpha", 0, "CRITICAL"),
        _ps("beta", 0, "CRITICAL"),
        _ps("beta", 1, "CRITICAL"),
        _ps("beta", 2, "CRITICAL"),
        _ps("alpha", 1, "HIGH"),  # alpha wins at HIGH but CRITICAL is checked first
        _ps("alpha", 2, "HIGH"),
        _ps("alpha", 3, "HIGH"),
        _ps("alpha", 4, "HIGH"),
    ]
    result = top_severity_class(problems, ["CRITICAL", "HIGH"])
    assert result == "beta", (
        "beta has 3 CRITICAL vs alpha 1 CRITICAL -> beta wins at top rank; got " + repr(result)
    )


def test_falls_through_when_top_severity_absent() -> None:
    """Falls through to next rank when top severity has no problems.

    Kills impl returning None when severity_order[0] has no problems.
    No CRITICAL problems. alpha: 2 HIGH. beta: 1 HIGH.
    Fall through to HIGH -> alpha wins (2 > 1).
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "HIGH"),
        _ps("beta", 0, "HIGH"),
    ]
    result = top_severity_class(problems, ["CRITICAL", "HIGH", "LOW"])
    assert result == "alpha", (
        "No CRITICAL; fall through to HIGH; alpha (2) > beta (1) -> alpha; got " + repr(result)
    )


def test_tie_break_ascending_class_name() -> None:
    """Tie at same rank broken by alphabetically ascending class name.

    Kills impl using reverse or arbitrary tie-break.
    alpha: 2 HIGH. beta: 2 HIGH. Tie -> 'alpha' wins (a < b).
    """
    problems = [
        _ps("beta", 0, "HIGH"),
        _ps("beta", 1, "HIGH"),
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "HIGH"),
    ]
    result = top_severity_class(problems, ["HIGH", "LOW"])
    assert result == "alpha", (
        "Tie at HIGH: alpha and beta both 2; alpha < beta -> alpha wins; got " + repr(result)
    )


def test_empty_severity_order_returns_none() -> None:
    """Empty severity_order -> None (cannot rank without order).

    Kills impl crashing with IndexError on empty ordering.
    """
    problems = [_ps("alpha", 0, "HIGH")]
    result = top_severity_class(problems, [])
    assert result is None, "empty ordering -> None; got " + repr(result)


def test_no_labelled_problems_returns_none() -> None:
    """No labelled problems (all unlabelled) -> None.

    Kills impl returning '' or raising.
    """
    problems = [_p("alpha", 0), _p("beta", 0)]
    result = top_severity_class(problems, ["CRITICAL", "HIGH"])
    assert result is None, "all-unlabelled -> None; got " + repr(result)
