"""Item 704: class_severity_above_threshold() -- count per class where rank > threshold.

class_severity_above_threshold(problems, threshold) -> dict[str, int].
Threshold is a rank int [0-4] (exclusive -- strictly above).
Zero-inclusive: classes with no above-threshold problems get count 0.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: STRICTLY above (not >=); class A: CRITICAL(4)+HIGH(3)+LOW(1),
     threshold=3 -> count=1 (only CRITICAL strictly above 3);
     >=impl gives 2 wrong (includes HIGH at rank=3).
  2. Threshold 0 -> all problems above (zero is the floor); all count.
  3. Empty -> {}.
  4. Multiple classes independent.
  5. Threshold above all ranks -> all counts = 0.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_above_threshold


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_strictly_above_not_gte_primary_discriminator() -> None:
    """PRIMARY DISC.: STRICTLY above threshold (not >=).

    class A: CRITICAL(4)+HIGH(3)+LOW(1), threshold=3 -> count=1.
    >=impl gives 2 (includes HIGH=3); kills off-by-one.
    """
    problems = [_p("A", "CRITICAL"), _p("A", "HIGH"), _p("A", "LOW")]
    result = class_severity_above_threshold(problems, 3)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be present; got {list(result)}"
    assert result["A"] == 1, (
        f"Only CRITICAL(4)>3; HIGH(3) NOT strictly above; got {result['A']} (>=impl=2 wrong)"
    )
    assert isinstance(result["A"], int), f"Must be int; got {type(result['A'])}"


def test_threshold_zero_counts_all_nonzero_ranks() -> None:
    """Threshold 0: INFO(0) NOT above 0; others are."""
    problems = [_p("B", "HIGH"), _p("B", "MEDIUM"), _p("B", "INFO")]
    result = class_severity_above_threshold(problems, 0)
    assert result["B"] == 2, f"HIGH(3)>0, MED(2)>0, INFO(0) NOT>0 -> 2; got {result.get('B')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_above_threshold([], 2) == {}


def test_multiple_classes_independent() -> None:
    """Each class counted independently."""
    problems = [_p("C", "CRITICAL"), _p("C", "MEDIUM")]  # C: rank>2 -> CRITICAL(4) only -> 1
    problems += [_p("D", "LOW"), _p("D", "INFO")]  # D: rank>2 -> 0
    result = class_severity_above_threshold(problems, 2)
    assert result["C"] == 1, f"C: CRITICAL>2 only -> 1; got {result.get('C')}"
    assert "D" in result, "'D' must be zero-inclusive present"
    assert result["D"] == 0, f"D: none above 2 -> 0; got {result.get('D')}"


def test_threshold_above_all_gives_zeros() -> None:
    """Threshold above all ranks -> all counts 0."""
    problems = [_p("E", "CRITICAL"), _p("E", "HIGH")]
    result = class_severity_above_threshold(problems, 4)
    assert result["E"] == 0, f"Nothing strictly above 4 -> 0; got {result.get('E')}"
