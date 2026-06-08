"""Item 696: class_severity_rank_avg() -- mean severity rank per class.

class_severity_rank_avg(problems) -> dict[str, float].
avg_rank = rank_sum / problem_count_for_class.  Float.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: avg_rank NOT rank_sum NOT count;
     class A: CRIT(4)+HIGH(3)+LOW(1) -> avg=(4+3+1)/3=2.667;
     rank_sum impl gives 8.0 wrong; count impl gives 3.0 wrong.
  2. Single problem -> avg equals that rank.
  3. Empty -> {}.
  4. Multiple classes computed independently.
  5. Return type is float.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_rank_avg


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_avg_rank_not_sum_not_count_primary_discriminator() -> None:
    """PRIMARY DISC.: value is avg rank; NOT rank_sum (8.0); NOT count (3.0).

    class A: CRIT(4)+HIGH(3)+LOW(1) -> avg = (4+3+1)/3 = 8/3 ≈ 2.667.
    rank_sum impl gives 8.0 wrong; count impl gives 3.0 wrong.
    """
    problems = [_p("A", "CRITICAL"), _p("A", "HIGH"), _p("A", "LOW")]
    result = class_severity_rank_avg(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be outer key; got {list(result)}"
    expected = (4 + 3 + 1) / 3
    assert abs(result["A"] - expected) < 1e-9, (
        f"(4+3+1)/3={expected:.6f}; got {result['A']:.6f} "
        f"(rank_sum=8.0 wrong, count=3.0 wrong)"
    )
    assert isinstance(result["A"], float), "Must be float"


def test_single_problem_avg_equals_rank() -> None:
    """Single CRITICAL problem -> avg = 4.0."""
    problems = [_p("B", "CRITICAL")]
    result = class_severity_rank_avg(problems)
    assert abs(result["B"] - 4.0) < 1e-9, f"CRIT=4.0; got {result.get('B')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_avg([]) == {}


def test_multiple_classes_independent() -> None:
    """Each class uses its own avg."""
    problems = [_p("X", "HIGH"), _p("X", "HIGH")]  # avg=(3+3)/2=3.0
    problems += [_p("Y", "LOW"), _p("Y", "MEDIUM")]  # avg=(1+2)/2=1.5
    result = class_severity_rank_avg(problems)
    assert abs(result["X"] - 3.0) < 1e-9, f"X: (3+3)/2=3.0; got {result.get('X')}"
    assert abs(result["Y"] - 1.5) < 1e-9, f"Y: (1+2)/2=1.5; got {result.get('Y')}"


def test_return_type_is_float() -> None:
    """Result values must be float not int."""
    result = class_severity_rank_avg([_p("Z", "HIGH"), _p("Z", "HIGH")])
    assert isinstance(result["Z"], float), f"Must be float; got {type(result['Z'])}"
    assert abs(result["Z"] - 3.0) < 1e-9
