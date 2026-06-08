"""Item 759: class_severity_rank_below_median() -- fraction below median rank per class.

class_severity_rank_below_median(problems) -> dict[str, float].
fraction = count(rank < median) / n per class.
All-same -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: below-median NOT above-median; class B: CRITICAL(4)*2+INFO(0)
     -> sorted=[0,4,4], median=4, count(< 4)=1, fraction=1/3~0.333;
     above-median-impl gives 0.0 wrong; all-zero-impl wrong.
  2. All-same -> 0.0 (no ranks strictly below median).
  3. Symmetric [INFO(0), CRITICAL(4)] -> median=2.0, below-count=1, fraction=0.5.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_below_median


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_below_not_above_primary_discriminator() -> None:
    """PRIMARY DISC.: below=1/3; above-median-impl gives 0.0 wrong.

    class B: CRITICAL*2+INFO -> sorted=[0,4,4], median=4, count(<4)=1, fraction=1/3.
    above_median for same data: count(>4)=0, fraction=0.0 — wrong.
    """
    problems = [_p("B", "CRITICAL"), _p("B", "CRITICAL"), _p("B", "INFO")]
    result = class_severity_rank_below_median(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "B" in result, f"'B' must be key; got {list(result)}"
    got = result["B"]
    assert math.isclose(got, 1 / 3, abs_tol=1e-9), (
        f"CRITICAL*2+INFO: median=4, below=1/3~{1/3:.6f}; got {got}"
    )
    assert not math.isclose(got, 0.0, abs_tol=1e-6), "Must be below not above (0.0 is above-impl)"


def test_all_same_gives_zero() -> None:
    """All same -> fraction = 0.0."""
    problems = [_p("C", "HIGH")] * 4
    result = class_severity_rank_below_median(problems)
    got = result.get("C")
    assert got is not None and math.isclose(got, 0.0, abs_tol=1e-9), (
        f"All HIGH -> 0.0; got {got}"
    )


def test_symmetric_two_gives_half() -> None:
    """INFO(0)+CRITICAL(4): median=2.0, count(< 2)=1, fraction=0.5."""
    problems = [_p("A", "INFO"), _p("A", "CRITICAL")]
    result = class_severity_rank_below_median(problems)
    got = result.get("A")
    assert got is not None and math.isclose(got, 0.5, abs_tol=1e-9), (
        f"INFO+CRITICAL: median=2.0, below=0.5; got {got}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_below_median([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("D", "CRITICAL"), _p("D", "CRITICAL"), _p("D", "INFO")]
    result = class_severity_rank_below_median(problems)
    assert isinstance(result["D"], float), f"Must be float; got {type(result['D'])}"
