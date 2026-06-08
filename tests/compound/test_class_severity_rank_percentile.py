"""Item 720: class_severity_rank_percentile() -- fraction at-or-below severity rank per class.

class_severity_rank_percentile(problems, severity) -> dict[str, float].
Fraction of problems in class with rank <= rank(severity).  [0.0, 1.0].
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: fraction AT-OR-BELOW rank (not count, not above);
     class A: CRITICAL+HIGH+LOW, severity='HIGH'(rank=3) -> 2/3 (HIGH+LOW have rank<=3);
     count-impl gives 2 wrong; above-impl gives 1/3 wrong.
  2. All at or below -> 1.0.
  3. Empty -> {}.
  4. Multiple classes independent.
  5. Severity = 'INFO' (rank=0) -> only INFO and unknowns count.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_rank_percentile


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_at_or_below_not_count_primary_discriminator() -> None:
    """PRIMARY DISC.: fraction at-or-below rank (not count; not above).

    class A: CRITICAL(4)+HIGH(3)+LOW(1), severity='HIGH'(rank=3).
    HIGH(3)<=3 and LOW(1)<=3 -> at_or_below=2; CRITICAL(4)>3 -> not counted.
    fraction=2/3. count-impl gives 2 wrong; above-impl gives 1/3 wrong.
    """
    problems = [_p("A", "CRITICAL"), _p("A", "HIGH"), _p("A", "LOW")]
    result = class_severity_rank_percentile(problems, "HIGH")
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be present; got {list(result)}"
    assert abs(result["A"] - 2 / 3) < 1e-9, (
        f"HIGH(3)+LOW(1) <= rank(HIGH)=3 -> 2/3; got {result['A']} (count=2 wrong)"
    )
    assert isinstance(result["A"], float), f"Must be float; got {type(result['A'])}"


def test_all_at_or_below_gives_one() -> None:
    """All problems below or at threshold -> 1.0."""
    problems = [_p("B", "INFO"), _p("B", "LOW"), _p("B", "MEDIUM")]
    result = class_severity_rank_percentile(problems, "CRITICAL")  # rank=4; all <= 4
    assert abs(result["B"] - 1.0) < 1e-9, f"All ranks <= CRITICAL(4) -> 1.0; got {result.get('B')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_percentile([], "HIGH") == {}


def test_multiple_classes_independent() -> None:
    """Each class fraction computed independently."""
    problems = [_p("C", "HIGH"), _p("C", "CRITICAL")]  # C: HIGH(3)<=3, CRIT(4)>3 -> 1/2
    problems += [_p("D", "LOW"), _p("D", "LOW")]        # D: both LOW(1)<=3 -> 2/2=1.0
    result = class_severity_rank_percentile(problems, "HIGH")
    assert abs(result["C"] - 0.5) < 1e-9, f"C: 1/2 -> 0.5; got {result.get('C')}"
    assert abs(result["D"] - 1.0) < 1e-9, f"D: 2/2 -> 1.0; got {result.get('D')}"


def test_info_threshold_only_counts_info() -> None:
    """severity='INFO' (rank=0): only INFO(0) and unknown(0) counted."""
    problems = [_p("E", "INFO"), _p("E", "INFO"), _p("E", "LOW")]
    result = class_severity_rank_percentile(problems, "INFO")  # rank=0
    assert abs(result["E"] - 2 / 3) < 1e-9, f"2 INFO(0)<=0; LOW(1)>0 -> 2/3; got {result.get('E')}"
