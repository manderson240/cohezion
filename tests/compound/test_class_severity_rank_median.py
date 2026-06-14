"""Item 728: class_severity_rank_median() -- median severity rank per class.

class_severity_rank_median(problems) -> dict[str, float].
Median rank (order statistic): middle value for odd, average two middle for even.
Single-problem -> that rank as float.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: median not mean; skewed distribution reveals the difference;
     class B: CRITICAL(4)*3+LOW(1) -> median=4.0 (middle of [1,4,4,4] is avg(4+4)/2=4.0);
     mean-impl gives (4+4+4+1)/4=3.25 wrong.
  2. Even count: average two middle values;
     class A: LOW(1)+MEDIUM(2)+HIGH(3)+CRITICAL(4) -> sorted [1,2,3,4] -> (2+3)/2=2.5.
  3. Single-problem -> that rank as float.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_median


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_median_not_mean_primary_discriminator() -> None:
    """PRIMARY DISC.: median not mean; skewed distribution separates them.

    class B: CRITICAL(4)*3+LOW(1) -> sorted [1,4,4,4] -> median=avg(4,4)=4.0.
    mean-impl gives (1+4+4+4)/4=3.25 wrong.
    """
    problems = [_p("B", "CRITICAL"), _p("B", "CRITICAL"), _p("B", "CRITICAL"), _p("B", "LOW")]
    result = class_severity_rank_median(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "B" in result, f"'B' must be present; got {list(result)}"
    got = result["B"]
    assert math.isclose(got, 4.0, abs_tol=1e-9), (
        f"CRIT*3+LOW: sorted [1,4,4,4] -> median=4.0; got {got} (mean-impl gives 3.25 wrong)"
    )


def test_even_count_average_two_middle() -> None:
    """Even count: average the two middle values after sorting.

    class A: LOW(1)+MEDIUM(2)+HIGH(3)+CRITICAL(4) -> sorted [1,2,3,4] -> (2+3)/2=2.5.
    """
    problems = [_p("A", "LOW"), _p("A", "MEDIUM"), _p("A", "HIGH"), _p("A", "CRITICAL")]
    result = class_severity_rank_median(problems)
    got = result.get("A")
    assert math.isclose(got, 2.5, abs_tol=1e-9), f"sorted [1,2,3,4] -> 2.5; got {got}"


def test_single_problem_returns_rank_as_float() -> None:
    """Single-problem class -> that rank as float."""
    result = class_severity_rank_median([_p("C", "HIGH")])
    got = result.get("C")
    assert math.isclose(got, 3.0, abs_tol=1e-9), f"Single HIGH(3) -> 3.0; got {got}"
    assert isinstance(got, float), f"Must be float; got {type(got)}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_median([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("D", "MEDIUM"), _p("D", "HIGH")]
    result = class_severity_rank_median(problems)
    assert isinstance(result["D"], float), f"Must be float; got {type(result['D'])}"
    # MEDIUM(2)+HIGH(3) -> sorted [2,3] -> (2+3)/2=2.5
    assert math.isclose(result["D"], 2.5, abs_tol=1e-9), f"MED+HIGH -> 2.5; got {result['D']}"
