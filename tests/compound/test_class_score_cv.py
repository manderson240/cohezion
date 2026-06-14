"""Item 533: class_score_cv() -- coefficient of variation of class total scores (2026-06-08).

``class_score_cv(problems, weights) -> float``:
Returns CV = std_dev / mean of class total weighted scores.
Dimensionless relative dispersion: normalises by mean for cross-scale comparison.
0.0 for empty, single class (std_dev=0), or mean==0.0.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns RATIO std_dev/mean (not raw std_dev).
     Kills impl reusing score_std_dev directly (would return std_dev alone).
  2. 0.0 when mean==0.0 (all unknown severity weights -> avoids division by zero).
     Kills impl dividing by zero when all class totals are 0.0.
  3. 0.0 for a single class (std_dev==0 -> cv==0 regardless of mean).
     Kills impl raising ZeroDivisionError for n=1.
  4. Higher CV for more spread-out data vs tightly-clustered data.
     Kills impl returning a fixed or wrong value.
  5. Empty -> 0.0 (not raise).
     Kills impl without the empty guard.
"""

from __future__ import annotations


from cohezion.compound.problem_discovery import Problem, class_score_cv


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_cv_ratio_not_std_dev() -> None:
    """PRIMARY DISC.: returns std_dev / mean, NOT std_dev alone.

    Classes A=1.0, B=5.0:
      mean = 3.0, std_dev = 2.0, CV = 2.0 / 3.0 ≈ 0.6667.
    score_std_dev would return 2.0.  CV returns 0.6667.
    Kills impl reusing score_std_dev (would return 2.0, not 0.6667).
    """
    problems = [
        _p("A", "f1", "LOW"),  # 1.0
        _p("B", "f2", "HIGH"),  # 5.0
    ]
    weights = {"LOW": 1.0, "HIGH": 5.0}
    result = class_score_cv(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    expected_cv = 2.0 / 3.0  # std_dev=2.0, mean=3.0
    assert abs(result - expected_cv) < 1e-9, (
        f"CV of [1.0, 5.0] = {expected_cv:.6f}; got {result} (2.0 = wrong: std_dev not CV)"
    )


def test_mean_zero_returns_zero() -> None:
    """All class totals == 0.0 -> mean==0.0 -> CV is undefined -> 0.0.

    Kills impl dividing std_dev by mean==0 (ZeroDivisionError).
    """
    # Unknown severity → weight defaults to 0.0
    problems = [
        _p("A", "f1", "UNKNOWN"),
        _p("B", "f2", "UNKNOWN"),
        _p("C", "f3", "UNKNOWN"),
    ]
    result = class_score_cv(problems, {"LOW": 1.0})  # UNKNOWN has no entry → 0.0
    assert result == 0.0, f"All-zero class totals -> mean=0 -> CV=0.0; got {result}"


def test_single_class_returns_zero() -> None:
    """Single class has std_dev=0 -> CV=0.0.

    Kills impl that raises ZeroDivisionError or produces NaN.
    """
    problems = [
        _p("OnlyClass", "f1", "HIGH"),
        _p("OnlyClass", "f2", "HIGH"),
    ]
    result = class_score_cv(problems, {"HIGH": 5.0})
    assert result == 0.0, f"Single class -> std_dev=0 -> CV=0.0; got {result}"


def test_higher_cv_for_more_spread_data() -> None:
    """More-spread distribution has higher CV than clustered distribution.

    Spread: [1.0, 9.0] -> CV = 4.0/5.0 = 0.8
    Tight:  [4.0, 6.0] -> CV = 1.0/5.0 = 0.2
    Kills impl returning a fixed or mean-independent value.
    """
    spread = [_p("A", "f1", "LOW"), _p("B", "f2", "HIGH")]
    tight = [_p("C", "f3", "MED_LO"), _p("D", "f4", "MED_HI")]
    w_spread = {"LOW": 1.0, "HIGH": 9.0}
    w_tight = {"MED_LO": 4.0, "MED_HI": 6.0}
    cv_spread = class_score_cv(spread, w_spread)
    cv_tight = class_score_cv(tight, w_tight)
    assert abs(cv_spread - 0.8) < 1e-9, f"CV of [1,9] = 0.8; got {cv_spread}"
    assert abs(cv_tight - 0.2) < 1e-9, f"CV of [4,6] = 0.2; got {cv_tight}"
    assert cv_spread > cv_tight, "More spread data must have higher CV"


def test_empty_returns_zero() -> None:
    """Empty problems -> 0.0 (not raise)."""
    result = class_score_cv([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"
