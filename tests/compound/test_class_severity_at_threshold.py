"""Item 706: class_severity_at_threshold() -- count per class where rank == threshold exactly.

class_severity_at_threshold(problems, threshold) -> dict[str, int].
Counts problems whose _SEVERITY_RANK equals threshold exactly.
Zero-inclusive.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: EXACTLY equal (not above, not >=);
     class A: HIGH(3)+MEDIUM(2)+HIGH(3), threshold=3 -> count=2;
     above-impl gives 0 (HIGH not > HIGH); >=impl gives 2+above wrong path.
  2. Nothing at threshold -> 0 (zero-inclusive).
  3. Empty -> {}.
  4. Multiple classes independent.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_at_threshold


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_exactly_equal_not_above_primary_discriminator() -> None:
    """PRIMARY DISC.: counts EXACTLY threshold rank (not above, not >=).

    class A: HIGH(3)+MEDIUM(2)+HIGH(3), threshold=3 -> count=2.
    above-impl gives 0 (no rank > 3); >=impl gives different wrong result path.
    """
    problems = [_p("A", "HIGH"), _p("A", "MEDIUM"), _p("A", "HIGH")]
    result = class_severity_at_threshold(problems, 3)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be present; got {list(result)}"
    assert result["A"] == 2, (
        f"Two HIGH(rank=3)==threshold(3) -> count=2; got {result['A']} "
        f"(above-impl=0 wrong, count-impl=3 wrong)"
    )
    assert isinstance(result["A"], int), f"Must be int; got {type(result['A'])}"


def test_nothing_at_threshold_gives_zero() -> None:
    """Class with nothing at exactly threshold -> 0 (zero-inclusive)."""
    problems = [_p("B", "CRITICAL"), _p("B", "LOW")]
    result = class_severity_at_threshold(problems, 2)  # MEDIUM=2; none present
    assert "B" in result, "'B' must be present (zero-inclusive)"
    assert result["B"] == 0, f"No MEDIUM -> 0; got {result.get('B')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_at_threshold([], 3) == {}


def test_multiple_classes_independent() -> None:
    """Each class computed independently."""
    problems = [_p("C", "HIGH"), _p("C", "HIGH"), _p("C", "LOW")]  # C: 2 at rank 3
    problems += [_p("D", "MEDIUM"), _p("D", "CRITICAL")]            # D: 1 at rank 2
    result = class_severity_at_threshold(problems, 3)
    assert result["C"] == 2, f"C: two HIGH at rank 3 -> 2; got {result.get('C')}"
    assert "D" in result, "'D' must be present"
    assert result["D"] == 0, f"D: no rank-3 -> 0; got {result.get('D')}"


def test_return_type_is_int() -> None:
    """Result values must be int."""
    problems = [_p("E", "CRITICAL")] * 3
    result = class_severity_at_threshold(problems, 4)  # CRITICAL=4
    assert isinstance(result["E"], int), f"Must be int; got {type(result['E'])}"
    assert result["E"] == 3, f"3 CRITICAL at rank 4 -> 3; got {result['E']}"
