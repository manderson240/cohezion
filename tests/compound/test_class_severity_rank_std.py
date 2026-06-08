"""Item 724: class_severity_rank_std() -- population std dev of severity ranks per class.

class_severity_rank_std(problems) -> dict[str, float].
Population std dev of _SEVERITY_RANK values per class.
Single-problem class -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: std dev NOT variance; class A: CRITICAL(4)+INFO(0) -> std=2.0;
     mean=2.0; deviations=[2,2]; variance=4.0; variance-impl gives 4.0 wrong;
     rank-avg gives 2.0 wrong (same numeric accident -- result type must be
     confirmed as std, not avg).
  2. Single-problem class -> 0.0.
  3. Empty -> {}.
  4. Multiple classes independent.
  5. All-same severity -> 0.0.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_std


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_std_not_variance_primary_discriminator() -> None:
    """PRIMARY DISC.: std dev NOT variance AND NOT avg.

    class A: CRITICAL(4)+INFO(0) -> std=2.0.
    variance-impl gives 4.0 wrong; mean-impl also gives 2.0 (same value,
    but use three-class case to confirm we compute spread not just average).
    Three-class: A: CRITICAL(4)+INFO(0), B: HIGH(3)+LOW(1) -> A=2.0, B=1.0.
    Avg would give A=2.0 B=2.0 (both wrong for B); variance gives A=4.0 B=1.0.
    """
    problems = [_p("A", "CRITICAL"), _p("A", "INFO")]  # A: ranks [4,0] -> std=2.0
    problems += [_p("B", "HIGH"), _p("B", "LOW")]  # B: ranks [3,1] -> std=1.0
    result = class_severity_rank_std(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be present; got {list(result)}"
    assert math.isclose(result["A"], 2.0, abs_tol=1e-9), (
        f"CRIT(4)+INFO(0): std=2.0; got {result['A']} "
        f"(variance-impl=4.0 wrong; avg=2.0 but B discriminates)"
    )
    assert math.isclose(result["B"], 1.0, abs_tol=1e-9), (
        f"HIGH(3)+LOW(1): std=1.0; got {result['B']} (avg-impl would give 2.0 wrong)"
    )


def test_single_problem_gives_zero() -> None:
    """Single-problem class -> 0.0 (zero deviation)."""
    result = class_severity_rank_std([_p("C", "HIGH")])
    assert math.isclose(result["C"], 0.0, abs_tol=1e-9), (
        f"Single HIGH -> 0.0; got {result.get('C')}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_std([]) == {}


def test_multiple_classes_independent() -> None:
    """Each class computes its own std independently."""
    problems = [_p("X", "CRITICAL"), _p("X", "CRITICAL")]  # X: [4,4] -> std=0.0
    problems += [_p("Y", "CRITICAL"), _p("Y", "INFO")]  # Y: [4,0] -> std=2.0
    result = class_severity_rank_std(problems)
    assert math.isclose(result["X"], 0.0, abs_tol=1e-9), (
        f"X: both CRIT -> 0.0; got {result.get('X')}"
    )
    assert math.isclose(result["Y"], 2.0, abs_tol=1e-9), (
        f"Y: CRIT+INFO -> 2.0; got {result.get('Y')}"
    )


def test_all_same_severity_gives_zero() -> None:
    """All same severity -> std = 0.0."""
    problems = [_p("Z", "MEDIUM")] * 4
    result = class_severity_rank_std(problems)
    assert math.isclose(result["Z"], 0.0, abs_tol=1e-9), f"4 MEDIUM -> 0.0; got {result.get('Z')}"
