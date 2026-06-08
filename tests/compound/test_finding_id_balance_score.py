"""Item 427: finding_id_balance_score() — normalised fid balance ratio (2026-06-08).

``finding_id_balance_score(problems) -> float``:
Returns finding_id_entropy / log2(num_distinct_fids).
0.0 = maximally imbalanced fids, 1.0 = perfectly balanced.
Empty -> 1.0.  Single fid -> 1.0.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on finding_id distribution (not class distribution).
     Kills impl reusing class_balance_score on wrong field.
  2. Equal fid distribution -> 1.0.
     Kills impl returning raw fid entropy.
  3. Single fid -> 1.0 (trivially balanced, not 0.0).
     Kills impl confusing balance with Gini impurity.
  4. Empty -> 1.0 (vacuously balanced, not raise).
     Kills impl with unguarded division.
  5. Unequal fid distribution -> value in (0, 1).
     Validates normalisation is meaningful.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    finding_id_balance_score,
)


def _p(fid: str, cls: str = "cls") -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_keyed_on_finding_id_not_class() -> None:
    """Balance is over finding_id distribution, not class distribution.

    PRIMARY DISCRIMINATOR: kills impl reusing class_balance_score.
    Two fids equally distributed -> 1.0; but we verify the key is fid, not class.
    """
    # 2 classes ('a','b'), 3 fids ('x','y','z') -- fid balance \!= class balance
    problems = [_p("x", "a"), _p("y", "a"), _p("z", "b"), _p("z", "b")]
    result = finding_id_balance_score(problems)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # fid x=1/4, y=1/4, z=2/4 -> NOT perfectly balanced (would be 1.0 if equal)
    assert result < 1.0, "Unequal fid distribution should give < 1.0; got " + repr(result)


def test_equal_fids_returns_one() -> None:
    """Equal fid distribution -> 1.0."""
    problems = [_p("fid_a"), _p("fid_b"), _p("fid_c"), _p("fid_d")]
    result = finding_id_balance_score(problems)
    assert abs(result - 1.0) < 1e-9, "Equal fids -> 1.0; got " + repr(result)


def test_single_fid_returns_one() -> None:
    """Single fid -> 1.0 (trivially balanced, not 0.0)."""
    problems = [_p("only"), _p("only"), _p("only")]
    result = finding_id_balance_score(problems)
    assert abs(result - 1.0) < 1e-9, "Single fid -> 1.0; got " + repr(result)


def test_empty_returns_one() -> None:
    """Empty input returns 1.0, not ZeroDivisionError."""
    result = finding_id_balance_score([])
    assert result == 1.0, "Empty -> 1.0; got " + repr(result)
    assert isinstance(result, float)


def test_unequal_fids_in_unit_interval() -> None:
    """Unequal fid distribution -> value strictly between 0 and 1."""
    problems = [_p("big"), _p("big"), _p("big"), _p("small")]
    result = finding_id_balance_score(problems)
    assert 0.0 < result < 1.0, "Unequal fids -> (0, 1); got " + repr(result)
