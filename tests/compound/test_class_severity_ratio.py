"""Item 690: class_severity_ratio() -- fraction of problems in class matching a given severity.

class_severity_ratio(problems, severity) -> dict[str, float].
Returns matching_count / total_class_count per class.
Zero-inclusive: classes with no matching severity get 0.0 (not absent).
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: denominator is CLASS-LOCAL total, NOT global total.
     class A: 3 problems, 2 HIGH -> ratio=2/3≈0.667 (not 2/5=0.4 global-total wrong).
     class B: 2 problems, 0 HIGH -> ratio=0.0.
  2. Zero-inclusive: class with no match returns 0.0 (not absent).
  3. Empty -> {}.
  4. All matching -> 1.0.
  5. Return type is float.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_ratio


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_class_local_denominator_primary_discriminator() -> None:
    """PRIMARY DISC.: ratio uses CLASS-LOCAL total (not global).

    class A: 3 problems, 2 HIGH -> ratio=2/3≈0.667.
    class B: 2 problems, 0 HIGH -> ratio=0.0.
    Global denominator (5) gives A=0.4 (WRONG).
    """
    problems = [_p("A", "HIGH"), _p("A", "HIGH"), _p("A", "LOW"),
                _p("B", "LOW"), _p("B", "MEDIUM")]
    result = class_severity_ratio(problems, "HIGH")
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"Class 'A' must be present; got {list(result)}"
    assert abs(result["A"] - 2/3) < 1e-9, (
        f"A: 2/3 HIGH (class-local denom=3); got {result['A']} "
        f"(0.4=global-denom wrong)"
    )
    assert isinstance(result["A"], float), "Must be float"
    assert "B" in result, "B must be present (zero-inclusive)"
    assert result["B"] == 0.0, (
        f"B: 0 HIGH out of 2 -> 0.0; got {result['B']}"
    )


def test_zero_inclusive_no_match_returns_zero() -> None:
    """Zero-inclusive: class present but no matching severity -> 0.0."""
    problems = [_p("C", "CRITICAL"), _p("C", "HIGH")]
    result = class_severity_ratio(problems, "LOW")
    assert "C" in result, "C must be present (zero-inclusive)"
    assert result["C"] == 0.0, f"C has no LOW -> 0.0; got {result['C']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_ratio([], "HIGH") == {}


def test_all_matching_ratio_one() -> None:
    """All problems have queried severity -> ratio=1.0."""
    problems = [_p("D", "HIGH"), _p("D", "HIGH"), _p("D", "HIGH")]
    result = class_severity_ratio(problems, "HIGH")
    assert result["D"] == 1.0, f"All HIGH -> 1.0; got {result.get('D')}"


def test_return_type_float() -> None:
    """Return type must be float even for exact fractions."""
    problems = [_p("E", "HIGH"), _p("E", "HIGH"), _p("E", "LOW")]
    result = class_severity_ratio(problems, "LOW")
    assert isinstance(result["E"], float), f"Must be float; got {type(result['E']).__name__}"
    assert abs(result["E"] - 1/3) < 1e-9, f"1/3 expected; got {result['E']}"
