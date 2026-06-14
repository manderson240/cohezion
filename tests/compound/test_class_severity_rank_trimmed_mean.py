"""Item 742: class_severity_rank_trimmed_mean() -- trimmed mean of severity ranks per class.

class_severity_rank_trimmed_mean(problems, trim_frac=0.1) -> dict[str, float].
Sorts ranks, removes floor(n*trim_frac) lowest and highest, mean of remainder.
n <= 2 -> plain mean.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: trimmed not plain; class A: [0,0,0,4,4], trim_frac=0.2
     -> removes 1 low=0, 1 high=4 -> mean([0,0,4])=4/3~1.333; plain-mean=1.6 wrong.
  2. Default trim_frac=0.1: n=5 -> floor(0.5)=0 -> same as plain mean.
  3. n <= 2 -> plain mean (not 0.0).
  4. Empty -> {}.
  5. Multiple classes independent.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_trimmed_mean


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_trimmed_not_plain_mean_primary_discriminator() -> None:
    """PRIMARY DISC.: trimmed\!=plain for skewed distribution.

    class A: INFO(0)*3+CRITICAL(4)*2 -> ranks [0,0,0,4,4]; trim_frac=0.2;
    removes 1 lowest=0, 1 highest=4 -> mean([0,0,4])=4/3~1.333;
    plain-mean=8/5=1.6 wrong.
    """
    problems = [
        _p("A", "INFO"),
        _p("A", "INFO"),
        _p("A", "INFO"),
        _p("A", "CRITICAL"),
        _p("A", "CRITICAL"),
    ]
    result = class_severity_rank_trimmed_mean(problems, trim_frac=0.2)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be present; got {list(result)}"
    got = result["A"]
    expected = 4 / 3  # mean([0,0,4]) = 1.333...
    assert math.isclose(got, expected, abs_tol=1e-9), (
        f"[0,0,0,4,4] trim=0.2 -> {expected:.6f}; got {got} (plain-mean=1.6 wrong)"
    )
    assert isinstance(got, float), f"Must be float; got {type(got)}"


def test_small_n_uses_plain_mean() -> None:
    """n <= 2 -> plain mean."""
    problems = [_p("B", "INFO"), _p("B", "CRITICAL")]  # [0,4] -> mean=2.0
    result = class_severity_rank_trimmed_mean(problems, trim_frac=0.2)
    got = result.get("B")
    assert math.isclose(got, 2.0, abs_tol=1e-9), f"n=2 -> plain mean=2.0; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_trimmed_mean([]) == {}


def test_default_trim_frac_no_trim_for_small_n() -> None:
    """Default trim_frac=0.1: floor(5*0.1)=0 -> no trimming."""
    problems = [
        _p("C", "INFO"),
        _p("C", "LOW"),
        _p("C", "MEDIUM"),
        _p("C", "HIGH"),
        _p("C", "CRITICAL"),
    ]  # [0,1,2,3,4] -> mean=2.0
    result = class_severity_rank_trimmed_mean(problems)  # default trim_frac=0.1
    got = result.get("C")
    assert math.isclose(got, 2.0, abs_tol=1e-9), f"floor(5*0.1)=0 -> plain mean=2.0; got {got}"


def test_multiple_classes_independent() -> None:
    """Each class computed independently."""
    problems = [
        _p("X", "INFO"),
        _p("X", "INFO"),
        _p("X", "INFO"),
        _p("X", "CRITICAL"),
        _p("X", "CRITICAL"),
    ] + [
        _p("Y", "MEDIUM"),
        _p("Y", "MEDIUM"),
        _p("Y", "MEDIUM"),
        _p("Y", "MEDIUM"),
        _p("Y", "MEDIUM"),
    ]
    result = class_severity_rank_trimmed_mean(problems, trim_frac=0.2)
    assert math.isclose(result["X"], 4 / 3, abs_tol=1e-9), f"X -> 4/3; got {result['X']}"
    assert math.isclose(result["Y"], 2.0, abs_tol=1e-9), f"Y all-MEDIUM -> 2.0; got {result['Y']}"
