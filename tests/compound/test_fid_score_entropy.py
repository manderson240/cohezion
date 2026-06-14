"""Item 544: fid_score_entropy() -- Shannon entropy of fid score distribution (2026-06-08).

``fid_score_entropy(problems, weights) -> float``:
Returns H = -sum(p_i * log2(p_i)) where p_i = fid_total_i / sum(fid_totals).
0.0 for empty, single fid, or zero total.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on FID axis, not class axis.
     All problems in ONE class, two fids -> class returns 0.0 (single class),
     fid returns non-zero.  Kills impl reusing class_score_entropy on wrong axis.
  2. Returns ENTROPY (bits), not CV.
     For equal fids [1.0, 1.0]: entropy = 1.0 bit, CV = 0.0.
     Kills impl reusing class_score_cv (returns 0.0, not 1.0).
  3. Uniform 3-fid distribution achieves log2(3) bits maximum.
     Kills impl using natural log (nats != bits).
  4. Single distinct fid -> 0.0 (certain distribution, H=0).
     Kills impl without the single-fid guard.
  5. Empty -> 0.0 (not raise).
     Kills impl without empty guard.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_score_entropy


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_fid_axis_entropy_not_class_axis() -> None:
    """PRIMARY DISC.: keyed on FID axis, not class axis.

    All problems in ONE class, two distinct fids fid_a=1.0 and fid_b=1.0:
      class_score_entropy: 1 class -> 0.0 (certain).
      fid_score_entropy: 2 equal fids -> 1.0 bit (maximum for 2).
    Kills impl reusing class_score_entropy (returns 0.0 for single class).
    """
    problems = [
        _p("SameClass", "fid_a", "EQUAL"),  # fid_a total = 1.0
        _p("SameClass", "fid_b", "EQUAL"),  # fid_b total = 1.0
    ]
    weights = {"EQUAL": 1.0}
    result = fid_score_entropy(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # class_score_entropy = 0.0 (1 class); fid_score_entropy = 1.0 bit (2 equal fids)
    assert abs(result - 1.0) < 1e-9, (
        f"Entropy of equal fids [1,1] = 1.0 bit; got {result} (0.0 = class axis is wrong)"
    )


def test_returns_entropy_not_cv() -> None:
    """Returns entropy (bits), not CV.

    Equal fids [5.0, 5.0]: entropy=1.0 bit; CV=0.0 (no spread).
    Kills impl reusing class_score_cv or fid_score_cv (returns 0.0 for equal values).
    """
    problems = [
        _p("A", "fid_a", "S5"),  # fid_a = 5.0
        _p("B", "fid_b", "S5"),  # fid_b = 5.0
    ]
    weights = {"S5": 5.0}
    result = fid_score_entropy(problems, weights)
    assert abs(result - 1.0) < 1e-9, (
        f"Entropy of equal fids [5,5] = 1.0 bit; got {result} (0.0 = CV of equal fids)"
    )


def test_uniform_three_fid_achieves_log2_3() -> None:
    """Uniform 3-fid distribution -> maximum entropy = log2(3) bits.

    Kills impl using natural log (nats: ln(3)=1.0986) or wrong normalization.
    """
    problems = [
        _p("A", "fid_a", "S3"),  # fid_a = 3.0
        _p("B", "fid_b", "S3"),  # fid_b = 3.0
        _p("C", "fid_c", "S3"),  # fid_c = 3.0
    ]
    weights = {"S3": 3.0}
    result = fid_score_entropy(problems, weights)
    expected = math.log2(3)
    assert abs(result - expected) < 1e-9, (
        f"Entropy of uniform [3,3,3] = log2(3) = {expected:.6f}; got {result} "
        f"(1.0986 = natural log is wrong)"
    )


def test_single_fid_returns_zero() -> None:
    """Single distinct fid -> all weight there -> H=0.0 (certain).

    Kills impl without single-fid guard.
    """
    problems = [
        _p("A", "only_fid", "HIGH"),
        _p("B", "only_fid", "HIGH"),
    ]
    result = fid_score_entropy(problems, {"HIGH": 5.0})
    assert result == 0.0, f"Single fid -> H=0.0; got {result}"


def test_empty_returns_zero() -> None:
    """Empty problems -> 0.0 (not raise)."""
    result = fid_score_entropy([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"
