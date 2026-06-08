"""Item 612: fid_severity_entropy() -- Shannon entropy of severity dist per fid.

``fid_severity_entropy(problems: list[Problem], fid: str) -> float``:
FID-axis complement of class_severity_entropy (item 260).
H = -Σ p·log₂(p) over labelled severities for that fid.
Unlabelled (empty severity) excluded from counts and total.
0.0 for single-severity, missing fid, or empty problems.

Discriminating tests:
  1. PRIMARY DISC.: takes fid not class; uniform 2-label -> 1.0 (log2(2)), not 0.5 (Gini).
     Kills impl reusing class_severity_entropy (would key on cls) or returning Gini.
  2. Unlabelled severity excluded from denominator.
     HIGH x2, unlabelled x2 -> H computed on 2 labelled only -> 0.0 (single label).
     Kills impl including unlabelled in total.
  3. Single-severity -> 0.0.
     Kills impl returning non-zero for single bucket.
  4. Unknown fid -> 0.0 (not raise).
     Kills impl raising KeyError for missing fid.
  5. Uniform 3-label -> log2(3) ≈ 1.585 bits.
     Kills impl using wrong normalization or wrong formula.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_entropy


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_entropy_not_gini_primary_discriminator() -> None:
    """PRIMARY DISC.: FID axis, entropy formula (1.0 for uniform 2-label), not Gini (0.5).

    fid 'f1' with HIGH=1, LOW=1 (uniform 2-label):
    H = -(0.5*log2(0.5) + 0.5*log2(0.5)) = 1.0.
    Gini = 1 - (0.5^2 + 0.5^2) = 0.5 (wrong formula).
    Kills impl reusing class_severity_entropy with wrong axis,
    and kills impl using Gini formula.
    """
    problems = [_p("A", "f1", "HIGH"), _p("B", "f1", "LOW")]
    result = fid_severity_entropy(problems, "f1")
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert abs(result - 1.0) < 1e-9, (
        f"Uniform 2-label -> H=1.0; got {result} (0.5 = Gini, not entropy)"
    )


def test_unlabelled_excluded_from_computation() -> None:
    """Unlabelled problems excluded from entropy (both count and denominator).

    fid 'f2' HIGH=2, unlabelled=2.
    Only labelled considered: 2 HIGH → single severity → H=0.0.
    Kills impl counting unlabelled in total (would give H>0 from dilution).
    """
    problems = [_p("A", "f2", "HIGH")] * 2 + [_p("A", "f2", "")]
    result = fid_severity_entropy(problems, "f2")
    assert abs(result) < 1e-9, (
        f"2 HIGH + 1 unlabelled -> single labelled severity -> H=0.0; got {result}"
    )


def test_single_severity_zero_entropy() -> None:
    """Single severity per fid -> H=0.0 (no uncertainty).

    Kills impl returning non-zero for a single bucket.
    """
    problems = [_p("A", "fy", "CRITICAL")] * 5
    result = fid_severity_entropy(problems, "fy")
    assert abs(result) < 1e-9, f"Single-severity -> H=0.0; got {result}"


def test_unknown_fid_returns_zero_not_raise() -> None:
    """Unknown fid -> 0.0 (not KeyError).

    Kills impl raising KeyError for missing fid.
    """
    problems = [_p("A", "f1", "HIGH")]
    result = fid_severity_entropy(problems, "nonexistent_fid")
    assert result == 0.0, f"Unknown fid -> 0.0; got {result}"


def test_uniform_three_label_entropy() -> None:
    """Uniform 3-label -> H = log2(3) ≈ 1.585 bits.

    fid 'fz': HIGH=1, MEDIUM=1, LOW=1.
    H = -(3 * 1/3 * log2(1/3)) = log2(3).
    Kills impl using wrong normalization.
    """
    problems = [_p("A", "fz", "HIGH"), _p("B", "fz", "MEDIUM"), _p("C", "fz", "LOW")]
    result = fid_severity_entropy(problems, "fz")
    expected = math.log2(3)
    assert abs(result - expected) < 1e-9, (
        f"Uniform 3-label -> H=log2(3)={expected:.6f}; got {result}"
    )
