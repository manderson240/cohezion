"""Item 293: labelling_coverage_fraction() — fraction of problems with a severity label (2026-06-08).

``labelling_coverage_fraction(problems: list[Problem]) -> float``:
Returns len(labelled) / len(total).  Empty or all-unlabelled -> 0.0.
All labelled -> 1.0.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: denominator is total problem count, NOT class count.
     Kills impl dividing by len(classes) instead of len(problems).
  2. Empty input -> 0.0 (not ZeroDivisionError).
     Kills impl that divides without empty guard.
  3. All unlabelled -> 0.0.
     Kills impl treating unlabelled as labelled.
  4. All labelled -> 1.0.
     Kills impl that over-counts or under-counts.
  5. Mixed -> exact fraction in (0.0, 1.0).
     Kills impl that rounds to 0 or 1 for mixed input.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    labelling_coverage_fraction,
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


def test_denominator_is_total_problems_not_classes() -> None:
    """Denominator is total problem count, not class count.

    PRIMARY DISCRIMINATOR: kills impl dividing by class count.
    3 classes, 6 problems (3 labelled, 3 unlabelled) -> 3/6 = 0.5, not 3/3 = 1.0.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _p("alpha", 1),  # unlabelled
        _ps("beta", 2, "LOW"),
        _p("beta", 3),  # unlabelled
        _ps("gamma", 4, "CRITICAL"),
        _p("gamma", 5),  # unlabelled
    ]
    result = labelling_coverage_fraction(problems)
    assert abs(result - 0.5) < 1e-9, "3 labelled / 6 total = 0.5; got " + repr(result)


def test_empty_input_returns_zero() -> None:
    """Empty input -> 0.0, not ZeroDivisionError.

    Kills impl without empty guard.
    """
    result = labelling_coverage_fraction([])
    assert result == 0.0, "Empty -> 0.0; got " + repr(result)


def test_all_unlabelled_returns_zero() -> None:
    """All unlabelled problems -> 0.0.

    Kills impl that counts unlabelled as labelled.
    """
    problems = [_p("alpha", 0), _p("beta", 1), _p("gamma", 2)]
    result = labelling_coverage_fraction(problems)
    assert result == 0.0, "All unlabelled -> 0.0; got " + repr(result)


def test_all_labelled_returns_one() -> None:
    """All labelled problems -> 1.0.

    Kills impl that over-counts or under-counts.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("beta", 1, "LOW"),
        _ps("gamma", 2, "CRITICAL"),
    ]
    result = labelling_coverage_fraction(problems)
    assert result == 1.0, "All labelled -> 1.0; got " + repr(result)


def test_mixed_returns_exact_fraction() -> None:
    """Mixed labelled/unlabelled -> exact float in (0.0, 1.0).

    Kills impl that rounds to 0 or 1 for mixed input.
    1 labelled out of 4 total -> 0.25.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _p("alpha", 1),
        _p("beta", 2),
        _p("gamma", 3),
    ]
    result = labelling_coverage_fraction(problems)
    assert abs(result - 0.25) < 1e-9, "1 labelled / 4 total = 0.25; got " + repr(result)
    assert 0.0 < result < 1.0, "Must be in (0.0, 1.0) for mixed input; got " + repr(result)
