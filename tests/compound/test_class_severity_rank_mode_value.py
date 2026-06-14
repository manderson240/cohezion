"""Item 776: class_severity_rank_mode_value() -- modal severity rank per class.

class_severity_rank_mode_value(problems) -> dict[str, float].
Returns the rank that appears most often per class; tie -> min rank as float.
All-same -> that rank.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: mode \!= mean; class A: [CRITICAL(4)*3, INFO(0)*2] -> mode=4.0;
     mean=2.4 wrong; median=4.0 same but tie-break test below distinguishes.
  2. Tie-break -> min rank: [INFO(0)*2, HIGH(3)*2, CRITICAL(4)] -> mode=0.0 (min of 0,3);
     median-impl gives 3.0 wrong.
  3. All-same -> that rank.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_mode_value


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_mode_not_mean_primary_discriminator() -> None:
    """PRIMARY DISC.: mode=4.0; mean=2.4 wrong.

    class A: [CRITICAL(4)*3, INFO(0)*2] -> counts={4:3, 0:2}, max_count=3, mode=4.
    """
    problems = [_p("A", "CRITICAL")] * 3 + [_p("A", "INFO")] * 2
    result = class_severity_rank_mode_value(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    assert math.isclose(got, 4.0, abs_tol=1e-9), f"CRITICAL*3+INFO*2 -> mode=4.0; got {got}"
    assert not math.isclose(got, 2.4, abs_tol=1e-6), "Must be mode not mean (2.4)"


def test_tie_break_gives_min_rank() -> None:
    """Tie -> min rank: [INFO(0)*2, HIGH(3)*2, CRITICAL(4)] -> mode=0.0.

    counts={0:2, 3:2, 4:1} -> tie between 0 and 3 -> min=0.
    median-impl gives 3.0 wrong.
    """
    problems = [_p("B", "INFO")] * 2 + [_p("B", "HIGH")] * 2 + [_p("B", "CRITICAL")]
    result = class_severity_rank_mode_value(problems)
    got = result.get("B")
    assert got is not None and math.isclose(got, 0.0, abs_tol=1e-9), (
        f"tie INFO+HIGH -> min=0.0; got {got}"
    )
    assert not math.isclose(got, 3.0, abs_tol=1e-6), "Must be min-tie not median (3.0)"


def test_all_same_gives_same_rank() -> None:
    """All same -> mode = that rank."""
    problems = [_p("C", "HIGH")] * 4
    result = class_severity_rank_mode_value(problems)
    got = result.get("C")
    assert got is not None and math.isclose(got, 3.0, abs_tol=1e-9), (
        f"All HIGH(3) -> mode=3.0; got {got}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_mode_value([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("D", "INFO"), _p("D", "INFO"), _p("D", "CRITICAL")]
    result = class_severity_rank_mode_value(problems)
    assert isinstance(result["D"], float), f"Must be float; got {type(result['D'])}"
