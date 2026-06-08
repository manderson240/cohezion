"""Item 424: finding_id_entropy() — Shannon entropy of the fid distribution (2026-06-08).

``finding_id_entropy(problems) -> float``:
Returns H = -sum(p * log2(p)) over finding_id_coverage_ratio values.
Two equal fids -> 1.0 bit.  Single fid -> 0.0.  Empty -> 0.0.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on finding_id histogram (not class histogram).
     Kills impl reusing class_entropy (wrong field).
  2. Two equal fids -> 1.0 bit (log2 base).
     Kills impl using natural log (would give ln(2) ≈ 0.693).
  3. Single fid -> 0.0 (no uncertainty).
     Validates degenerate case.
  4. Empty -> 0.0 (not ZeroDivisionError).
     Kills impl with unguarded division.
  5. Unequal fid distribution -> correct entropy value.
     Validates general formula.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    finding_id_entropy,
)


def _p(fid: str, cls: str = "cls") -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_keyed_on_finding_id_not_class() -> None:
    """Entropy is over finding_id distribution, not class distribution.

    PRIMARY DISCRIMINATOR: kills impl reusing class_entropy.
    Different entropy when class and fid distributions diverge.
    """
    # 2 classes (alpha/beta), 3 distinct fids — fid entropy != class entropy
    problems = [
        _p("fid_x", "alpha"),
        _p("fid_y", "alpha"),
        _p("fid_z", "beta"),
        _p("fid_z", "beta"),
    ]
    result = finding_id_entropy(problems)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # fid_x=1/4, fid_y=1/4, fid_z=2/4 -> H != 1.0 (class entropy would be 1.0)
    assert abs(result - 1.0) > 0.01, (
        "fid entropy should differ from class entropy here; got " + repr(result)
    )


def test_two_equal_fids_returns_one_bit() -> None:
    """Two equal-frequency fids -> H = 1.0 bit (log2, not ln)."""
    problems = [_p("fid_a"), _p("fid_b")]
    result = finding_id_entropy(problems)
    assert abs(result - 1.0) < 1e-9, "Two equal fids -> 1.0 bit; got " + repr(result)


def test_single_fid_returns_zero() -> None:
    """Single fid -> H = 0.0 (certain outcome)."""
    problems = [_p("only"), _p("only"), _p("only")]
    result = finding_id_entropy(problems)
    assert abs(result - 0.0) < 1e-9, "Single fid -> 0.0; got " + repr(result)


def test_empty_returns_zero() -> None:
    """Empty input returns 0.0, not ZeroDivisionError."""
    result = finding_id_entropy([])
    assert result == 0.0, "Empty -> 0.0; got " + repr(result)
    assert isinstance(result, float)


def test_unequal_fid_distribution_correct_entropy() -> None:
    """Unequal fid distribution returns correct Shannon entropy.

    fid_a=2/4=1/2, fid_b=1/4, fid_c=1/4.
    H = -(1/2*log2(1/2) + 1/4*log2(1/4) + 1/4*log2(1/4))
      = -(−0.5 + −0.5 + −0.5) = 1.5 bits
    """
    problems = [_p("fid_a"), _p("fid_a"), _p("fid_b"), _p("fid_c")]
    result = finding_id_entropy(problems)
    assert abs(result - 1.5) < 1e-9, "H should be 1.5 bits; got " + repr(result)
