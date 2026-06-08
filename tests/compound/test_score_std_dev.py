"""Item 521: score_std_dev() -- population standard deviation of class total scores (2026-06-08).

``score_std_dev(problems, weights) -> float``:
Returns the population standard deviation (sqrt of population variance) of all
class total weighted severity scores.
0.0 for empty input or single class.  0.0 when all classes tie.
Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns STD-DEV (not variance).
     Kills impl returning score_variance directly.
  2. 0.0 for empty (not raise).
     Kills impl without empty guard.
  3. 0.0 for single class.
     Kills impl returning NaN or raising for n=1.
  4. sqrt of POPULATION variance (not sample variance).
     Kills impl using statistics.stdev (sample, n-1).
  5. 0.0 when all classes tie (zero std-dev for uniform distribution).
     Kills impl that only checks n < 2.
"""

from __future__ import annotations

import math

from cohezion.compound.problem_discovery import (
    Problem,
    score_std_dev,
    score_variance,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_stddev_not_variance() -> None:
    """PRIMARY DISC.: returns std-dev (not variance).

    ClassA=9.0, ClassB=1.0; mean=5.0; variance=16.0; std-dev=4.0.
    Kills impl returning score_variance directly (which would return 16.0).
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),   # 9.0
        _p("ClassB", "f2", "LOW"),    # 1.0
    ]
    result = score_std_dev(problems, {"HIGH": 9.0, "LOW": 1.0})
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert math.isclose(result, 4.0, rel_tol=1e-9), "std-dev = 4.0; got " + repr(result)
    assert not math.isclose(result, 16.0, rel_tol=1e-9), "Must not return variance (16.0)"


def test_empty_input_returns_zero() -> None:
    """Empty input -> 0.0 (not raise).

    Kills impl calling math.sqrt(empty variance) if variance raised.
    """
    result = score_std_dev([], {"HIGH": 3.0})
    assert result == 0.0, "Empty -> 0.0; got " + repr(result)
    assert isinstance(result, float)


def test_single_class_returns_zero() -> None:
    """Single class -> 0.0 (not raise, not NaN).

    Kills impl that takes sqrt of NaN or raises for n=1.
    """
    problems = [_p("Only", "f1", "HIGH"), _p("Only", "f2", "LOW")]
    result = score_std_dev(problems, {"HIGH": 5.0, "LOW": 1.0})
    assert result == 0.0, "Single class -> 0.0; got " + repr(result)


def test_sqrt_of_population_variance() -> None:
    """std-dev == sqrt(population variance).

    Verifies the relationship between score_std_dev and score_variance.
    ClassA=6.0, ClassB=2.0; population variance=4.0; std-dev=2.0.
    Sample std-dev (wrong) would be sqrt(8.0) ≈ 2.828.
    Kills impl using statistics.stdev (n-1 sample).
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),   # 6.0
        _p("ClassB", "f2", "LOW"),    # 2.0
    ]
    weights = {"HIGH": 6.0, "LOW": 2.0}
    var = score_variance(problems, weights)   # 4.0 population variance
    std = score_std_dev(problems, weights)
    assert math.isclose(std, math.sqrt(var), rel_tol=1e-9), (
        f"std-dev must be sqrt(variance); sqrt({var})={math.sqrt(var):.4f}; got {std}"
    )
    assert math.isclose(std, 2.0, rel_tol=1e-9), "sqrt(4.0) = 2.0; got " + repr(std)


def test_all_classes_tie_returns_zero() -> None:
    """All classes at same total score -> 0.0 (zero std-dev).

    Kills impl that only guards n < 2 but doesn't handle uniform distribution.
    """
    problems = [
        _p("A", "f1", "HIGH"),   # 3.0
        _p("B", "f2", "HIGH"),   # 3.0
        _p("C", "f3", "HIGH"),   # 3.0
    ]
    result = score_std_dev(problems, {"HIGH": 3.0})
    assert result == 0.0, "All tied -> std-dev=0.0; got " + repr(result)
