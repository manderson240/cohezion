"""Item 423: class_entropy() -- Shannon entropy of the class distribution (2026-06-08).

``class_entropy(problems) -> float``:
Returns the Shannon entropy of the class histogram in bits (using log base-2).
H = -sum(p * log2(p)) where p = class_count / total_records.
Empty -> 0.0.  Single class -> 0.0.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: uses log2 (bits), not natural log.
     Kills impl using math.log (nats) — two equal classes would give ln(2)~0.693.
  2. Empty -> 0.0 (not raise or nan).
     Kills impl with unguarded log(0) or division.
  3. Single class -> 0.0 (p=1.0, log2(1)=0).
     Validates degenerate single-class case.
  4. Two equal classes -> exactly 1.0 bit.
     Kills impl with wrong formula or wrong base.
  5. Unequal distribution -> correct entropy value.
     Validates general formula.
"""

from __future__ import annotations

import math

from cohezion.compound.problem_discovery import (
    Problem,
    class_entropy,
)


def _p(cls: str, fid: str = "f") -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_uses_log2_not_natural_log() -> None:
    """Uses log2 (bits) not natural log.

    PRIMARY DISCRIMINATOR: two equal classes -> 1.0 bit (not ln(2)~0.693 nats).
    """
    problems = [_p("a"), _p("b")]  # two equal classes, each 0.5
    result = class_entropy(problems)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert abs(result - 1.0) < 1e-9, (
        "Two equal classes -> 1.0 bit; got "
        + repr(result)
        + " (ln(2)~0.693 means log was used instead of log2)"
    )


def test_empty_returns_zero() -> None:
    """Empty input returns 0.0, not raise."""
    result = class_entropy([])
    assert result == 0.0, "Empty -> 0.0; got " + repr(result)
    assert isinstance(result, float)


def test_single_class_returns_zero() -> None:
    """Single class -> 0.0 (p=1.0, -1.0*log2(1.0)=0.0)."""
    problems = [_p("only"), _p("only"), _p("only")]
    result = class_entropy(problems)
    assert abs(result - 0.0) < 1e-9, "Single class -> 0.0; got " + repr(result)


def test_two_equal_classes_returns_one_bit() -> None:
    """Two equal-probability classes -> 1.0 bit."""
    problems = [_p("alpha"), _p("alpha"), _p("beta"), _p("beta")]
    result = class_entropy(problems)
    assert abs(result - 1.0) < 1e-9, "Two equal classes -> 1.0; got " + repr(result)


def test_unequal_distribution_correct_entropy() -> None:
    """Unequal distribution returns correct Shannon entropy value.

    3 classes: p_a=1/2, p_b=1/4, p_c=1/4.
    H = -(0.5*log2(0.5) + 0.25*log2(0.25) + 0.25*log2(0.25))
      = -(0.5*(-1) + 0.25*(-2) + 0.25*(-2))
      = -(-0.5 - 0.5 - 0.5) = 1.5 bits
    """
    problems = [_p("a"), _p("a"), _p("b"), _p("c")]
    result = class_entropy(problems)
    expected = 1.5
    assert abs(result - expected) < 1e-9, "p_a=1/2, p_b=1/4, p_c=1/4 -> H=1.5 bits; got " + repr(
        result
    )
