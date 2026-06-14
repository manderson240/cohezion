"""Item 499: all_score_summaries() -- bulk score stats for all classes (2026-06-08).

``all_score_summaries(problems, weights) -> dict[str, dict[str, float]]``:
Returns {cls: {'total': ..., 'mean': ..., 'max_single': ...}} for every class.
Each inner dict has exactly the 3 keys from score_summary.
Empty problems -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns dict of dicts (not flat dict).
     all_score_summaries returns {'ClassA': {'total': ..., 'mean': ..., 'max_single': ...}}.
     Kills impl reusing all_severity_scores (returns dict[str, float], not nested).
  2. Each inner dict has 3 keys: total, mean, max_single.
     Kills impl that only stores the total float.
  3. max_single is per-class (not global max).
     ClassA max=HIGH=3.0, ClassB max=LOW=1.0 -> different max_single per class.
     Kills impl using global max across all classes.
  4. Empty problems -> {} (not raise).
     Kills impl without empty guard.
  5. Equivalent to calling score_summary per class individually.
     Kills impl with inconsistent per-class calculation.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    all_score_summaries,
    score_summary,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


WEIGHTS = {"HIGH": 3.0, "LOW": 1.0}


def test_returns_dict_of_dicts_not_flat() -> None:
    """PRIMARY DISC.: returns dict[str, dict[str, float]], not dict[str, float].

    ClassA appears -> result['ClassA'] is a dict with 3 keys.
    Kills impl reusing all_severity_scores (flat float values).
    """
    problems = [_p("ClassA", "f1", "HIGH"), _p("ClassA", "f2", "LOW")]
    result = all_score_summaries(problems, WEIGHTS)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "ClassA" in result
    inner = result["ClassA"]
    assert isinstance(inner, dict), "Inner must be dict; got " + repr(type(inner))
    assert set(inner.keys()) == {"total", "mean", "max_single"}, (
        "Inner must have total/mean/max_single; got " + repr(set(inner.keys()))
    )


def test_max_single_is_per_class_not_global() -> None:
    """max_single is computed per-class, not globally across all classes.

    ClassA: HIGH only (max=3.0); ClassB: LOW only (max=1.0).
    Kills impl returning global max=3.0 for all classes.
    """
    problems = [_p("ClassA", "f1", "HIGH"), _p("ClassB", "f2", "LOW")]
    result = all_score_summaries(problems, WEIGHTS)
    assert abs(result["ClassA"]["max_single"] - 3.0) < 1e-9, "ClassA max_single=3.0; got " + repr(
        result["ClassA"]
    )
    assert abs(result["ClassB"]["max_single"] - 1.0) < 1e-9, "ClassB max_single=1.0; got " + repr(
        result["ClassB"]
    )


def test_empty_problems_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise)."""
    result = all_score_summaries([], WEIGHTS)
    assert result == {}, "Empty -> {}; got " + repr(result)


def test_equivalent_to_individual_score_summary_calls() -> None:
    """bulk result equals calling score_summary per class individually."""
    problems = [
        _p("ClassA", "f1", "HIGH"),
        _p("ClassA", "f2", "LOW"),
        _p("ClassB", "f3", "HIGH"),
        _p("ClassB", "f4", "HIGH"),
        _p("ClassB", "f5", "LOW"),
    ]
    bulk = all_score_summaries(problems, WEIGHTS)
    for cls in ["ClassA", "ClassB"]:
        expected = score_summary(problems, cls, WEIGHTS)
        for key in ["total", "mean", "max_single"]:
            assert abs(bulk[cls][key] - expected[key]) < 1e-9, (
                f"cls={cls} key={key}: bulk={bulk[cls][key]}, expected={expected[key]}"
            )


def test_all_classes_appear_in_result() -> None:
    """Every class from the problem list appears as a key."""
    problems = [_p("X", "f1", "HIGH"), _p("Y", "f2", "LOW"), _p("Z", "f3", "HIGH")]
    result = all_score_summaries(problems, WEIGHTS)
    assert set(result.keys()) == {"X", "Y", "Z"}, "All 3 classes present; got " + repr(
        set(result.keys())
    )
