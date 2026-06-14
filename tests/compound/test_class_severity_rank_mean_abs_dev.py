"""Item 740: class_severity_rank_mean_abs_dev() -- MAD of severity ranks per class.

class_severity_rank_mean_abs_dev(problems) -> dict[str, float].
MAD = mean(|xi - mean|).  n=1 -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: MAD not std; class A: INFO(0)+CRITICAL(4) -> mean=2, MAD=2.0;
     std-impl gives sqrt(8)~2.828 wrong (uses squared deviations).
  2. All-same -> 0.0.
  3. n=1 -> 0.0.
  4. Empty -> {}.
  5. Multiple classes independent.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_mean_abs_dev


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_mad_not_std_primary_discriminator() -> None:
    """PRIMARY DISC.: MAD = mean(|xi-mean|) \!= sample_std.

    class A: INFO(0)+CRITICAL(4) -> mean=2, MAD=2.0;
    std-impl gives sqrt(8)~2.828 wrong.
    """
    problems = [_p("A", "INFO"), _p("A", "CRITICAL")]
    result = class_severity_rank_mean_abs_dev(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be present; got {list(result)}"
    got = result["A"]
    assert math.isclose(got, 2.0, abs_tol=1e-9), (
        f"[0,4] -> MAD=2.0; got {got} (std-impl gives ~2.828 wrong)"
    )
    assert isinstance(got, float), f"Must be float; got {type(got)}"


def test_all_same_gives_zero() -> None:
    """All-same severity -> MAD=0.0."""
    problems = [_p("B", "HIGH")] * 4
    result = class_severity_rank_mean_abs_dev(problems)
    got = result.get("B")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"All HIGH -> MAD=0.0; got {got}"


def test_single_problem_gives_zero() -> None:
    """n=1 -> MAD=0.0."""
    result = class_severity_rank_mean_abs_dev([_p("C", "CRITICAL")])
    got = result.get("C")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"n=1 -> MAD=0.0; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_mean_abs_dev([]) == {}


def test_multiple_classes_independent() -> None:
    """Each class computed independently."""
    problems = [_p("X", "INFO"), _p("X", "CRITICAL")]  # [0,4] -> MAD=2.0
    problems += [_p("Y", "MEDIUM"), _p("Y", "MEDIUM")]  # all-same -> MAD=0.0
    result = class_severity_rank_mean_abs_dev(problems)
    assert math.isclose(result["X"], 2.0, abs_tol=1e-9), f"X [0,4] -> 2.0; got {result['X']}"
    assert math.isclose(result["Y"], 0.0, abs_tol=1e-9), f"Y all-same -> 0.0; got {result['Y']}"
