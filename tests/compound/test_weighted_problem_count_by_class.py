"""Item 504: weighted_problem_count_by_class() -- per-class scalar totals (2026-06-08).

``weighted_problem_count_by_class(problems, weights) -> dict[str, float]``:
Returns {class: total_weighted_score} for every class in the problem set.
The scalar-first alternative to all_score_summaries (only total, no mean/max_single).
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns dict[str, float] (flat), not dict of dicts.
     Kills impl returning all_score_summaries which has nested {total, mean, max_single}.
  2. Only the TOTAL per class (no mean/max_single keys inside values).
     Kills impl returning all_score_summaries['ClassA'] directly.
  3. Empty input -> {} (not raise).
     Kills impl without empty guard.
  4. Class with only unknown-severity records maps to 0.0.
     Kills impl omitting zero-weight classes.
  5. Multiple records per class accumulate correctly.
     Kills impl counting only distinct severities.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    weighted_problem_count_by_class,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_flat_dict_not_nested() -> None:
    """PRIMARY DISC.: returns dict[str, float] (flat), not dict of dicts.

    Values must be floats, not dicts like {total: ..., mean: ..., max_single: ...}.
    Kills impl reusing all_score_summaries.
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),
        _p("ClassB", "f2", "LOW"),
    ]
    weights = {"HIGH": 5.0, "LOW": 1.0}
    result = weighted_problem_count_by_class(problems, weights)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "ClassA" in result, "ClassA must be present; got " + repr(result)
    assert isinstance(result["ClassA"], float), "Values must be float; got " + repr(
        type(result["ClassA"])
    )
    # Values must NOT be dicts (kills all_score_summaries path)
    assert not isinstance(result["ClassA"], dict), "Values must not be dicts; got " + repr(
        result["ClassA"]
    )
    assert result == {"ClassA": 5.0, "ClassB": 1.0}, "Flat totals; got " + repr(result)


def test_only_total_not_mean_or_max() -> None:
    """Values are plain floats, not dicts with total/mean/max_single keys.

    Kills impl returning all_score_summaries[cls] directly.
    """
    problems = [_p("X", "f1", "HIGH"), _p("X", "f2", "HIGH")]
    weights = {"HIGH": 3.0}
    result = weighted_problem_count_by_class(problems, weights)
    assert result == {"X": 6.0}, "Two HIGH = 6.0; got " + repr(result)


def test_empty_input_returns_empty_dict() -> None:
    """Empty input -> {} (not raise)."""
    result = weighted_problem_count_by_class([], {"HIGH": 3.0})
    assert result == {}, "Empty -> {}; got " + repr(result)


def test_unknown_severity_maps_to_zero() -> None:
    """Class with only unknown-severity records maps to 0.0 (not omitted).

    Kills impl that skips zero-weight classes.
    """
    problems = [
        _p("Known", "f1", "HIGH"),
        _p("Unknown", "f2", "GHOST"),
    ]
    weights = {"HIGH": 5.0}
    result = weighted_problem_count_by_class(problems, weights)
    assert "Unknown" in result, "Unknown-sev class must be present; got " + repr(result)
    assert result["Unknown"] == 0.0, "Unknown-sev -> 0.0; got " + repr(result)


def test_multiple_records_accumulate() -> None:
    """Multiple records per class accumulate to correct total.

    ClassA: HIGH(3.0) + LOW(1.0) + HIGH(3.0) = 7.0.
    Kills impl counting distinct severities instead of records.
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),
        _p("ClassA", "f2", "LOW"),
        _p("ClassA", "f3", "HIGH"),
        _p("ClassB", "f4", "LOW"),
    ]
    result = weighted_problem_count_by_class(problems, {"HIGH": 3.0, "LOW": 1.0})
    assert result["ClassA"] == 7.0, "3+1+3=7; got " + repr(result)
    assert result["ClassB"] == 1.0, "1.0; got " + repr(result)
