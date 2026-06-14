"""Item 382: unlabelled_fraction() — fraction of problems without a severity label (2026-06-08).

``unlabelled_fraction(problems) -> float``:
Returns unlabelled_count / total_count as a float in [0.0, 1.0].
Complement of labelled_fraction: labelled_fraction + unlabelled_fraction == 1.0 for non-empty.
Empty input -> 0.0.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: 1.0 when ALL problems are unlabelled.
     Kills impl that always returns 0.0 or confuses labelled/unlabelled.
  2. 0.0 when ALL problems are labelled.
     Kills impl returning labelled_fraction (swapped numerator).
  3. Complement invariant: labelled_fraction + unlabelled_fraction == 1.0.
     Kills impl that computes independently without the complement relationship.
  4. Empty input returns 0.0, not 1.0 or ZeroDivisionError.
     Kills impl with unguarded division or treating empty as "all unlabelled".
  5. Mixed case: correct ratio (counts all records, not distinct IDs).
     Kills impl using len(set(...)) instead of len(...).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    labelled_fraction,
    unlabelled_fraction,
)


def _p(cls: str, fid: str, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_all_unlabelled_returns_one() -> None:
    """All unlabelled problems -> 1.0.

    PRIMARY DISCRIMINATOR: kills impl always returning 0.0 or confusing
    labelled/unlabelled.
    """
    problems = [_p("a", "f:0"), _p("b", "f:1"), _p("c", "f:2")]
    result = unlabelled_fraction(problems)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert abs(result - 1.0) < 1e-9, "All unlabelled -> 1.0; got " + repr(result)


def test_all_labelled_returns_zero() -> None:
    """All labelled problems -> 0.0.

    Kills impl returning labelled_fraction (swapped numerator).
    """
    problems = [_p("a", "f:0", "HIGH"), _p("b", "f:1", "LOW"), _p("c", "f:2", "MEDIUM")]
    result = unlabelled_fraction(problems)
    assert abs(result - 0.0) < 1e-9, "All labelled -> 0.0; got " + repr(result)


def test_complement_invariant_holds() -> None:
    """labelled_fraction + unlabelled_fraction == 1.0 for any non-empty input.

    Kills impl that computes independently rather than as complement.
    """
    problems = [_p("a", "f:0", "HIGH"), _p("b", "f:1"), _p("c", "f:2", "LOW")]
    lf = labelled_fraction(problems)
    uf = unlabelled_fraction(problems)
    assert abs(lf + uf - 1.0) < 1e-9, f"labelled ({lf:.4f}) + unlabelled ({uf:.4f}) must equal 1.0"


def test_empty_returns_zero_not_one() -> None:
    """Empty input returns 0.0 — NOT 1.0 or ZeroDivisionError.

    Kills impl treating empty as 'all unlabelled' -> 1.0.
    """
    result = unlabelled_fraction([])
    assert result == 0.0, "Empty -> 0.0 (not 1.0); got " + repr(result)
    assert isinstance(result, float), "Must be float; got " + repr(type(result))


def test_mixed_ratio_counts_records_not_ids() -> None:
    """3 unlabelled out of 5 total = 0.6 (counts all records, not distinct IDs)."""
    problems = [
        _p("a", "f:0", "HIGH"),
        _p("b", "f:1", "LOW"),
        _p("c", "f:2"),  # unlabelled
        _p("d", "f:3"),  # unlabelled
        _p("e", "f:4"),  # unlabelled
    ]
    result = unlabelled_fraction(problems)
    assert abs(result - 0.6) < 1e-9, "3 of 5 unlabelled = 0.6; got " + repr(result)
