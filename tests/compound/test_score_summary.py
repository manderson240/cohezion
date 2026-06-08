"""Item 498: score_summary() -- per-class scoring statistics dict (2026-06-08).

``score_summary(problems, problem_class, weights) -> dict[str, float]``:
Returns {'total': ..., 'mean': ..., 'max_single': ...}.
total = sum of all weights for the class.
mean = total / count (0.0 when class absent/empty).
max_single = max weight of any single matching problem (0.0 when absent).
All three keys always present.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns dict with exactly 3 keys (total/mean/max_single).
     Kills impl reusing class_total_severity_score (returns float, not dict).
  2. mean \!= total when count > 1.
     ClassA: HIGH x2 + LOW x1 -> total=7.0, mean=7.0/3≈2.33.
     Kills impl setting mean=total.
  3. max_single is the single-record maximum weight (not total/count).
     ClassA: HIGH(3.0) + HIGH(3.0) + LOW(1.0) -> max_single=3.0 not 2.33.
     Kills impl computing max_single as mean.
  4. Absent class -> {'total': 0.0, 'mean': 0.0, 'max_single': 0.0}.
     Kills impl without absence guard.
  5. Unknown severity contributes 0 to all three stats.
     ClassA has only UNKNOWN_SEV -> total=0.0, mean=0.0, max_single=0.0.
     Kills impl that raises on missing weight key.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    score_summary,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


WEIGHTS = {"HIGH": 3.0, "LOW": 1.0}


def test_returns_dict_with_three_keys() -> None:
    """PRIMARY DISC.: returns dict with keys total, mean, max_single (not float).

    Kills impl returning class_total_severity_score (a float).
    """
    problems = [_p("ClassA", "f1", "HIGH"), _p("ClassA", "f2", "HIGH")]
    result = score_summary(problems, "ClassA", WEIGHTS)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert set(result.keys()) == {"total", "mean", "max_single"}, (
        "Must have exactly keys total/mean/max_single; got " + repr(set(result.keys()))
    )


def test_mean_differs_from_total_when_count_gt_1() -> None:
    """mean = total / count; differs from total when count > 1.

    ClassA: HIGH x2 (6.0) + LOW x1 (1.0) -> total=7.0, mean=7.0/3≈2.333.
    Kills impl setting mean=total (would give mean=7.0).
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),
        _p("ClassA", "f2", "HIGH"),
        _p("ClassA", "f3", "LOW"),
    ]
    result = score_summary(problems, "ClassA", WEIGHTS)
    assert abs(result["total"] - 7.0) < 1e-9, "total=7.0; got " + repr(result["total"])
    expected_mean = 7.0 / 3
    assert abs(result["mean"] - expected_mean) < 1e-6, (
        f"mean={expected_mean:.4f}; got " + repr(result["mean"])
    )


def test_max_single_is_record_max_not_mean() -> None:
    """max_single is the highest single-record weight, not mean.

    ClassA: HIGH(3.0) + HIGH(3.0) + LOW(1.0) -> max_single=3.0 (not 2.33).
    Kills impl computing max_single as mean.
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),
        _p("ClassA", "f2", "HIGH"),
        _p("ClassA", "f3", "LOW"),
    ]
    result = score_summary(problems, "ClassA", WEIGHTS)
    assert abs(result["max_single"] - 3.0) < 1e-9, (
        "max_single=3.0 (HIGH weight); got " + repr(result["max_single"])
    )


def test_absent_class_all_zeros() -> None:
    """Absent class -> {'total': 0.0, 'mean': 0.0, 'max_single': 0.0}."""
    problems = [_p("ClassA", "f1", "HIGH")]
    result = score_summary(problems, "NONEXISTENT", WEIGHTS)
    assert result == {"total": 0.0, "mean": 0.0, "max_single": 0.0}, (
        "Absent -> all zeros; got " + repr(result)
    )


def test_unknown_severity_contributes_zero() -> None:
    """Unknown severity (missing weight key) contributes 0 to all stats."""
    problems = [_p("ClassA", "f1", "UNKNOWN_SEV")]
    result = score_summary(problems, "ClassA", WEIGHTS)
    assert result["total"] == 0.0, "Unknown sev -> total=0.0; got " + repr(result)
    assert result["mean"] == 0.0, "Unknown sev -> mean=0.0; got " + repr(result)
    assert result["max_single"] == 0.0, "Unknown sev -> max_single=0.0; got " + repr(result)
