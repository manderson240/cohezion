"""Item 736: class_severity_rank_cv() -- coefficient of variation of severity ranks per class.

class_severity_rank_cv(problems) -> dict[str, float].
CV = sample_std / mean; mean=0 -> 0.0; n <= 1 -> 0.0.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: CV not std; class A: LOW(1)+HIGH(3) -> mean=2, std=sqrt(2)~1.414;
     CV=sqrt(2)/2~0.707; std-impl gives sqrt(2)~1.414 wrong (no mean normalization).
  2. mean=0 -> 0.0 (divide-by-zero guard).
  3. n <= 1 -> 0.0.
  4. Empty -> {}.
  5. Multiple classes independent.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_cv


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_cv_not_std_primary_discriminator() -> None:
    """PRIMARY DISC.: CV = std/mean, NOT just std.

    class A: LOW(1)+HIGH(3) -> ranks [1,3]; mean=2, std=sqrt(2); CV=sqrt(2)/2~0.707.
    std-impl gives sqrt(2)~1.414 wrong (unnormalized).
    """
    problems = [_p("A", "LOW"), _p("A", "HIGH")]
    result = class_severity_rank_cv(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be present; got {list(result)}"
    got = result["A"]
    expected = math.sqrt(2) / 2  # ~0.707107
    assert math.isclose(got, expected, abs_tol=1e-6), (
        f"[1,3] -> CV=sqrt(2)/2~{expected:.6f}; got {got} "
        f"(std-impl gives sqrt(2)~1.414 wrong)"
    )
    assert isinstance(got, float), f"Must be float; got {type(got)}"


def test_mean_zero_gives_zero() -> None:
    """All INFO (rank=0) -> mean=0 -> CV=0.0 (no divide-by-zero)."""
    problems = [_p("B", "INFO"), _p("B", "INFO"), _p("B", "INFO")]
    result = class_severity_rank_cv(problems)
    got = result.get("B")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"All INFO -> CV=0.0; got {got}"


def test_single_problem_gives_zero() -> None:
    """n <= 1 per class -> 0.0."""
    result = class_severity_rank_cv([_p("C", "CRITICAL")])
    got = result.get("C")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"n=1 -> 0.0; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_cv([]) == {}


def test_multiple_classes_independent() -> None:
    """Each class computed independently."""
    problems = [_p("X", "LOW"), _p("X", "HIGH")]  # [1,3] -> CV=sqrt(2)/2
    problems += [_p("Y", "CRITICAL"), _p("Y", "CRITICAL")]  # all-same -> std=0 -> CV=0
    result = class_severity_rank_cv(problems)
    assert math.isclose(result["X"], math.sqrt(2) / 2, abs_tol=1e-6), (
        f"X [1,3] -> CV~0.707; got {result['X']}"
    )
    assert math.isclose(result["Y"], 0.0, abs_tol=1e-9), (
        f"Y all-same -> CV=0.0; got {result['Y']}"
    )
