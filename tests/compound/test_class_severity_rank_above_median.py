"""Item 757: class_severity_rank_above_median() -- fraction above median rank per class.

class_severity_rank_above_median(problems) -> dict[str, float].
fraction = count(rank > median_rank) / n per class.
Symmetric dist -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: above-median fraction not median value;
     class A: INFO(0)*2+CRITICAL(4) -> sorted [0,0,4], median=0, count(>0)=1,
     fraction=1/3~0.333; median-impl gives 0.0 wrong; count-impl gives 1 wrong.
  2. Symmetric [0,4] -> median=2.0; count(>2)=1; fraction=0.5 (not 1.0).
  3. All-same -> fraction=0.0 (none exceed median).
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations

import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_above_median


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_above_median_fraction_primary_discriminator() -> None:
    """PRIMARY DISC.: fraction=1/3; median_value=0.0 wrong; count=1 wrong.

    class A: INFO(0)*2+CRITICAL(4) -> sorted [0,0,4]; median=0; count(>0)=1; frac=1/3.
    """
    problems = [_p("A", "INFO"), _p("A", "INFO"), _p("A", "CRITICAL")]
    result = class_severity_rank_above_median(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be present; got {list(result)}"
    got = result["A"]
    expected = 1 / 3
    assert math.isclose(got, expected, abs_tol=1e-9), (
        f"INFO*2+CRITICAL -> fraction=1/3~{expected:.6f}; got {repr(got)} "
        f"(median_value=0.0 wrong, count=1 wrong)"
    )
    assert isinstance(got, float), f"Must be float; got {type(got)}"


def test_symmetric_two_gives_half() -> None:
    """INFO(0)+CRITICAL(4) -> median=2.0; count(>2)=1; fraction=0.5."""
    problems = [_p("B", "INFO"), _p("B", "CRITICAL")]
    result = class_severity_rank_above_median(problems)
    got = result.get("B")
    assert math.isclose(got, 0.5, abs_tol=1e-9), (
        f"INFO+CRITICAL: median=2.0; fraction=0.5; got {repr(got)}"
    )


def test_all_same_gives_zero() -> None:
    """All-same severity -> fraction=0.0 (no rank exceeds median)."""
    problems = [_p("C", "HIGH")] * 5
    result = class_severity_rank_above_median(problems)
    got = result.get("C")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"All HIGH -> fraction=0.0; got {repr(got)}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_above_median([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    result = class_severity_rank_above_median(
        [_p("D", "INFO"), _p("D", "INFO"), _p("D", "CRITICAL")]
    )
    assert isinstance(result["D"], float), f"Must be float; got {type(result['D'])}"
