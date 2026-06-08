"""Item 336: max_severity_span_class() — class with the greatest severity span (2026-06-08).

``max_severity_span_class(problems) -> str | None``:
Delegates to severity_span; returns the class_name with the highest span count.
Tie-break: ascending class name.  None when no labelled problems.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns class with HIGHEST SPAN not first class seen.
     Kills insertion-order impl.
  2. Tie-break ascending class name.
     Kills reverse or arbitrary tie-break.
  3. None when no labelled problems (all unlabelled or empty input).
     Kills impl returning '' or first class unconditionally.
  4. Single class with 1 severity returns that class.
     Kills impl returning None on non-empty input.
  5. Empty input returns None.
     Kills impl raising on empty.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    max_severity_span_class,
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


def test_returns_class_with_highest_span() -> None:
    """Returns class with the most distinct severities.

    PRIMARY DISCRIMINATOR: kills insertion-order impl.
    alpha: 1 severity (HIGH). beta: 3 severities (HIGH/LOW/CRITICAL).
    beta has max span -> beta wins.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("beta", 0, "HIGH"),
        _ps("beta", 1, "LOW"),
        _ps("beta", 2, "CRITICAL"),
    ]
    result = max_severity_span_class(problems)
    assert result == "beta", (
        "beta span=3 > alpha span=1 -> beta; got " + repr(result)
    )


def test_tie_break_ascending_class_name() -> None:
    """Tie on span broken by ascending class name.

    Kills reverse or arbitrary tie-break.
    alpha: HIGH+LOW (span=2). beta: HIGH+LOW (span=2). Tie -> alpha wins (a < b).
    """
    problems = [
        _ps("beta", 0, "HIGH"), _ps("beta", 1, "LOW"),
        _ps("alpha", 0, "HIGH"), _ps("alpha", 1, "LOW"),
    ]
    result = max_severity_span_class(problems)
    assert result == "alpha", (
        "Tie at span=2; alpha < beta -> alpha wins; got " + repr(result)
    )


def test_none_when_no_labelled_problems() -> None:
    """None when all problems are unlabelled.

    Kills impl returning '' or first class unconditionally.
    """
    problems = [_p("alpha", 0), _p("beta", 0)]
    result = max_severity_span_class(problems)
    assert result is None, "all unlabelled -> None; got " + repr(result)


def test_single_class_returns_that_class() -> None:
    """Single class with 1 severity returns the class name.

    Kills impl returning None on non-empty input.
    """
    problems = [_ps("alpha", 0, "HIGH")]
    result = max_severity_span_class(problems)
    assert result == "alpha", "single class 'alpha' -> 'alpha'; got " + repr(result)


def test_empty_input_returns_none() -> None:
    """Empty input returns None without raising."""
    result = max_severity_span_class([])
    assert result is None, "empty -> None; got " + repr(result)
