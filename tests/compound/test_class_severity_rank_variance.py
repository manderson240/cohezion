"""Item 726: class_severity_rank_variance() -- population variance of severity ranks per class.

class_severity_rank_variance(problems) -> dict[str, float].
variance = mean((rank-mean)^2).  Single-problem -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: variance not std dev;
     class A: CRITICAL(4)+INFO(0) -> var=4.0 (mean=2.0; sq_dev=4+4=8; /2=4.0);
     std-impl gives 2.0 wrong; avg-impl gives 2.0 wrong.
  2. Single problem -> 0.0.
  3. Empty -> {}.
  4. Multiple classes independent.
  5. Uniform ranks -> 0.0 (zero variance).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_rank_variance


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_variance_not_std_primary_discriminator() -> None:
    """PRIMARY DISC.: variance (not sqrt); class A: CRITICAL(4)+INFO(0) -> var=4.0.

    mean=2.0; sq_devs=[4,4]; mean=4.0. std-impl gives 2.0 wrong.
    """
    problems = [_p("A", "CRITICAL"), _p("A", "INFO")]
    result = class_severity_rank_variance(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be present; got {list(result)}"
    assert abs(result["A"] - 4.0) < 1e-9, (
        f"CRITICAL(4)+INFO(0) -> var=4.0; got {result['A']} (std=2.0 wrong)"
    )
    assert isinstance(result["A"], float), f"Must be float; got {type(result['A'])}"


def test_single_problem_gives_zero() -> None:
    """Single problem -> variance = 0.0."""
    problems = [_p("B", "HIGH")]
    result = class_severity_rank_variance(problems)
    assert result["B"] == 0.0, f"Single problem -> 0.0; got {result.get('B')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_variance([]) == {}


def test_multiple_classes_independent() -> None:
    """Each class variance computed independently."""
    problems = [_p("C", "CRITICAL")] * 3  # C: uniform -> var=0.0
    problems += [_p("D", "CRITICAL"), _p("D", "INFO")]  # D: var=4.0
    result = class_severity_rank_variance(problems)
    assert abs(result["C"] - 0.0) < 1e-9, f"C uniform -> var=0.0; got {result.get('C')}"
    assert abs(result["D"] - 4.0) < 1e-9, f"D CRIT+INFO -> var=4.0; got {result.get('D')}"


def test_three_values_variance() -> None:
    """HIGH(3)+MEDIUM(2)+LOW(1): mean=2.0; sq_devs=[1,0,1]; var=2/3."""
    problems = [_p("E", "HIGH"), _p("E", "MEDIUM"), _p("E", "LOW")]
    result = class_severity_rank_variance(problems)
    expected = 2 / 3
    assert abs(result["E"] - expected) < 1e-9, (
        f"HIGH+MED+LOW -> var={expected:.6f}; got {result.get('E')}"
    )
