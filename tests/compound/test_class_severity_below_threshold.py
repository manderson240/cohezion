"""Item 708: class_severity_below_threshold() -- count per class where rank < threshold.

class_severity_below_threshold(problems, threshold) -> dict[str, int].
Strictly below threshold.  Zero-inclusive.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: strictly BELOW (rank < threshold, not <=);
     class A: INFO(0)+LOW(1)+HIGH(3), threshold=2 -> count=2;
     <=impl gives 3 wrong (includes LOW+INFO+anything at rank 2).
     Wait: INFO(0)<2 ✓, LOW(1)<2 ✓, HIGH(3)<2 ✗ -> count=2.
     <=impl would give same 2 for this example. Better: threshold=1;
     INFO(0)<1 -> count=1; <=impl gives 2 (INFO+LOW at rank<=1).
  2. Nothing below threshold -> 0 (zero-inclusive).
  3. Empty -> {}.
  4. Multiple classes independent.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_below_threshold


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_strictly_below_not_lte_primary_discriminator() -> None:
    """PRIMARY DISC.: strictly below (rank < threshold, not <=).

    class A: INFO(0)+LOW(1)+MEDIUM(2), threshold=1 -> count=1 (only INFO strictly below 1).
    <=impl gives 2 (INFO+LOW at rank<=1); kills <=impl.
    """
    problems = [_p("A", "INFO"), _p("A", "LOW"), _p("A", "MEDIUM")]
    result = class_severity_below_threshold(problems, 1)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be present; got {list(result)}"
    assert result["A"] == 1, (
        f"INFO(0)<1 only; LOW(1) NOT strictly below 1 -> count=1; "
        f"got {result['A']} (<=impl=2 wrong)"
    )
    assert isinstance(result["A"], int), f"Must be int; got {type(result['A'])}"


def test_nothing_below_threshold_gives_zero() -> None:
    """Class with nothing strictly below threshold -> 0 (zero-inclusive)."""
    problems = [_p("B", "CRITICAL"), _p("B", "HIGH")]
    result = class_severity_below_threshold(problems, 3)  # only CRITICAL(4)>=3, HIGH(3)>=3
    assert "B" in result, "'B' must be present (zero-inclusive)"
    assert result["B"] == 0, f"CRIT(4)+HIGH(3) not <3 -> 0; got {result.get('B')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_below_threshold([], 2) == {}


def test_multiple_classes_independent() -> None:
    """Each class computed independently."""
    problems = [_p("C", "INFO"), _p("C", "LOW"), _p("C", "HIGH")]  # C: INFO+LOW <2 -> 2
    problems += [_p("D", "HIGH"), _p("D", "CRITICAL")]              # D: none <2 -> 0
    result = class_severity_below_threshold(problems, 2)
    assert result["C"] == 2, f"C: INFO(0)+LOW(1) <2 -> 2; got {result.get('C')}"
    assert "D" in result, "'D' must be present"
    assert result["D"] == 0, f"D: none <2 -> 0; got {result.get('D')}"


def test_return_type_is_int() -> None:
    """Result values must be int."""
    problems = [_p("E", "INFO")] * 3
    result = class_severity_below_threshold(problems, 1)
    assert isinstance(result["E"], int), f"Must be int; got {type(result['E'])}"
    assert result["E"] == 3, f"3 INFO(0)<1 -> 3; got {result['E']}"
