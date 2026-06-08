"""Item 786: class_severity_rank_fraction_at_or_above() -- fraction at or above threshold per class.

class_severity_rank_fraction_at_or_above(problems, threshold: int) -> dict[str, float].
fraction = count(rank >= threshold) / n per class.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: at-or-above not exact; [CRIT*3, HIGH*2] fraction_at_or_above(3)=1.0;
     fraction_at_or_above(4)=0.6; count_at_rank(3)-impl=0.4 wrong.
  2. Threshold above all -> 0.0.
  3. Threshold below all -> 1.0.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_fraction_at_or_above


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_at_or_above_not_exact_primary_discriminator() -> None:
    """PRIMARY DISC.: fraction_at_or_above(3)=1.0; count_at_rank(3)/n=0.4 wrong.

    class A: [CRITICAL(4)*3, HIGH(3)*2].
    fraction(rank>=3): 5/5=1.0.
    fraction(rank>=4): 3/5=0.6.
    count_at_rank(3)/n: 2/5=0.4 (wrong -- misses CRITICAL).
    """
    problems = [_p("A", "CRITICAL")] * 3 + [_p("A", "HIGH")] * 2
    result3 = class_severity_rank_fraction_at_or_above(problems, 3)
    assert isinstance(result3, dict), "Must return dict"
    assert "A" in result3, f"'A' must be key; got {list(result3)}"
    got3 = result3["A"]
    assert math.isclose(got3, 1.0, abs_tol=1e-9), (
        f"fraction_at_or_above(3) for [CRIT*3,HIGH*2] = 1.0; got {got3}"
    )
    result4 = class_severity_rank_fraction_at_or_above(problems, 4)
    got4 = result4["A"]
    assert math.isclose(got4, 0.6, abs_tol=1e-9), (
        f"fraction_at_or_above(4) for [CRIT*3,HIGH*2] = 0.6; got {got4}"
    )
    # Discriminator: at-or-above(3)=1.0 \!= count_at_rank(3)/n=0.4
    assert not math.isclose(got3, 0.4, abs_tol=1e-6), "Must be at-or-above not exact"


def test_threshold_above_all_gives_zero() -> None:
    """Threshold higher than any rank -> 0.0."""
    problems = [_p("B", "HIGH")] * 3  # rank=3
    result = class_severity_rank_fraction_at_or_above(problems, 4)  # CRITICAL=4
    got = result.get("B")
    assert got is not None and math.isclose(got, 0.0, abs_tol=1e-9), (
        f"All HIGH(3) with threshold=4 -> 0.0; got {got}"
    )


def test_threshold_below_all_gives_one() -> None:
    """Threshold at or below minimum rank -> 1.0."""
    problems = [_p("C", "CRITICAL")] * 4  # rank=4
    result = class_severity_rank_fraction_at_or_above(problems, 4)
    got = result.get("C")
    assert got is not None and math.isclose(got, 1.0, abs_tol=1e-9), (
        f"All CRITICAL(4) with threshold=4 -> 1.0; got {got}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_fraction_at_or_above([], 3) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("D", "HIGH"), _p("D", "INFO")]
    result = class_severity_rank_fraction_at_or_above(problems, 3)
    assert isinstance(result["D"], float), f"Must be float; got {type(result['D'])}"
