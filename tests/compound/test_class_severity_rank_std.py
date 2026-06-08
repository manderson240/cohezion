"""Item 724: class_severity_rank_std() -- population std dev of severity ranks per class.

class_severity_rank_std(problems) -> dict[str, float].
Population std dev (not sample).  Single-problem -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: std dev not variance, not avg;
     class A: CRITICAL(4)+INFO(0) -> std=2.0 (mean=2.0; var=4.0; sqrt=2.0);
     variance-impl gives 4.0 wrong; avg-impl gives 2.0 (right value wrong reason -- caught by test 5).
  2. Single problem -> 0.0.
  3. Empty -> {}.
  4. Multiple classes independent.
  5. Uniform ranks -> 0.0 (no variance).
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_std


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_std_not_variance_primary_discriminator() -> None:
    """PRIMARY DISC.: std dev = sqrt(variance); class A: CRITICAL(4)+INFO(0) -> std=2.0.

    mean=2.0; deviations [2,-2]; variance=4.0; std=sqrt(4)=2.0.
    variance-impl gives 4.0 wrong; kills variance impl.
    """
    problems = [_p("A", "CRITICAL"), _p("A", "INFO")]
    result = class_severity_rank_std(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be present; got {list(result)}"
    assert abs(result["A"] - 2.0) < 1e-9, (
        f"CRITICAL(4)+INFO(0): std=2.0; got {result['A']} (variance=4.0 wrong)"
    )
    assert isinstance(result["A"], float), f"Must be float; got {type(result['A'])}"


def test_single_problem_gives_zero() -> None:
    """Single problem per class -> std = 0.0."""
    problems = [_p("B", "HIGH")]
    result = class_severity_rank_std(problems)
    assert result["B"] == 0.0, f"Single problem -> std=0.0; got {result.get('B')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_std([]) == {}


def test_multiple_classes_independent() -> None:
    """Each class std dev computed independently."""
    # C: ranks [4,4,4] -> std=0.0
    problems = [_p("C", "CRITICAL")] * 3
    # D: ranks [4,0] -> std=2.0
    problems += [_p("D", "CRITICAL"), _p("D", "INFO")]
    result = class_severity_rank_std(problems)
    assert abs(result["C"] - 0.0) < 1e-9, f"C uniform -> std=0.0; got {result.get('C')}"
    assert abs(result["D"] - 2.0) < 1e-9, f"D CRITICAL+INFO -> std=2.0; got {result.get('D')}"


def test_three_values_std() -> None:
    """Three ranks: HIGH(3)+MEDIUM(2)+LOW(1) -> mean=2.0; var=2/3; std=sqrt(2/3)."""
    problems = [_p("E", "HIGH"), _p("E", "MEDIUM"), _p("E", "LOW")]
    result = class_severity_rank_std(problems)
    expected = math.sqrt(2 / 3)
    assert abs(result["E"] - expected) < 1e-9, (
        f"HIGH+MED+LOW -> std={expected:.6f}; got {result.get('E')}"
    )
