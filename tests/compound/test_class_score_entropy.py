"""Item 543: class_score_entropy() -- Shannon entropy of class total scores (2026-06-08).

``class_score_entropy(problems, weights) -> float``:
Returns the Shannon entropy (in bits, log base 2) of the normalized per-class
total weighted score distribution.  p_i = class_total_i / sum(class_totals).
H = -sum(p_i * log2(p_i)).  0.0 for empty, single class, or zero total.
Maximum when all class totals are equal (uniform distribution).  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns ENTROPY (not CV) -- different measure for same data.
     For [1.0, 1.0]: entropy = 1.0 bit (certain uniform), CV = 0.0.
     Kills impl reusing class_score_cv (would return 0.0, not 1.0).
  2. Uniform distribution achieves maximum entropy = log2(n).
     Kills impl not correctly normalizing to probabilities.
  3. Single class -> 0.0 (certain distribution: p=1.0, H=-1*log2(1)=0).
     Kills impl without the n<2 or zero-entropy guard.
  4. 0.0 for empty (not raise).
     Kills impl without empty guard.
  5. Operates on class TOTAL scores, not raw per-problem severity values.
     Kills impl computing entropy over individual problem severity weights.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_score_entropy


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_entropy_not_cv() -> None:
    """PRIMARY DISC.: returns Shannon entropy (bits), not CV.

    Two equal classes [1.0, 1.0]:
      entropy = 1.0 bit (uniform 2-class = maximum entropy)
      CV = std_dev / mean = 0.0 / 1.0 = 0.0 (no spread)
    Kills impl reusing class_score_cv (returns 0.0 for equal classes, not 1.0).
    """
    problems = [
        _p("A", "f1", "LOW"),  # A total = 1.0
        _p("B", "f2", "LOW"),  # B total = 1.0
    ]
    weights = {"LOW": 1.0}
    result = class_score_entropy(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # entropy([0.5, 0.5]) = 1.0 bit; CV = 0.0 -- must not be 0.0
    assert abs(result - 1.0) < 1e-9, (
        f"Entropy of equal classes [1,1] = 1.0 bit; got {result} (0.0 = CV of equal classes)"
    )


def test_uniform_distribution_achieves_log2_n() -> None:
    """Uniform n-class distribution achieves maximum entropy = log2(n).

    Three equal classes [5.0, 5.0, 5.0]:
      p_i = 1/3 for each; H = log2(3) = 1.58496...
    Kills impl not normalizing to probability distribution.
    """
    problems = [
        _p("A", "f1", "S5"),  # 5.0
        _p("B", "f2", "S5"),  # 5.0
        _p("C", "f3", "S5"),  # 5.0
    ]
    weights = {"S5": 5.0}
    result = class_score_entropy(problems, weights)
    expected = math.log2(3)
    assert abs(result - expected) < 1e-9, (
        f"Entropy of uniform [5,5,5] = log2(3) = {expected:.6f}; got {result}"
    )


def test_single_class_returns_zero() -> None:
    """Single class -> 0.0 (certain distribution: H = 0 bits).

    Kills impl not guarding for n=1 (would compute -1.0*log2(1.0) = 0.0 anyway,
    but the guard is needed to avoid ZeroDivisionError when computing total).
    """
    problems = [_p("OnlyClass", "f1", "HIGH")]
    weights = {"HIGH": 5.0}
    result = class_score_entropy(problems, weights)
    assert result == 0.0, f"Single class -> entropy = 0.0; got {result}"


def test_empty_returns_zero() -> None:
    """Empty problems -> 0.0 (not raise)."""
    result = class_score_entropy([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"


def test_uses_class_total_scores_not_individual_severities() -> None:
    """Computes entropy over per-class TOTAL probabilities, not individual weights.

    Class A: 2x HIGH(5.0) -> total 10.0; B=3.0; C=1.0. Sum=14.0.
    Class probs: [10/14, 3/14, 1/14].
    Individual severity values: [1.0, 3.0, 5.0, 5.0], sum=14.0.
    Individual probs: [1/14, 3/14, 5/14, 5/14].
    The entropies are different -- class aggregation matters.
    """
    problems = [
        _p("A", "f1", "HIGH"),  # +5.0
        _p("A", "f2", "HIGH"),  # A total = 10.0
        _p("B", "f3", "LOW"),  # B total = 3.0
        _p("C", "f4", "V_LOW"),  # C total = 1.0
    ]
    weights = {"HIGH": 5.0, "LOW": 3.0, "V_LOW": 1.0}
    result = class_score_entropy(problems, weights)

    # Class probs [10/14, 3/14, 1/14]:
    total = 14.0
    class_probs = [10.0 / total, 3.0 / total, 1.0 / total]
    expected_class = -sum(p * math.log2(p) for p in class_probs if p > 0)

    # Individual probs [5/14, 5/14, 3/14, 1/14]:
    ind_probs = [5.0 / total, 5.0 / total, 3.0 / total, 1.0 / total]
    expected_ind = -sum(p * math.log2(p) for p in ind_probs if p > 0)

    assert isinstance(result, float), "Must return float"
    assert abs(result - expected_class) < 1e-9, (
        f"Class-aggregated entropy = {expected_class:.6f}; got {result} "
        f"(individual entropy = {expected_ind:.6f} is wrong)"
    )
