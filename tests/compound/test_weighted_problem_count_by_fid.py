"""Item 505: weighted_problem_count_by_fid() -- per-fid scalar totals (2026-06-08).

``weighted_problem_count_by_fid(problems, weights) -> dict[str, float]``:
Returns {fid: total_weighted_score} for every finding_id in the problem set,
accumulated across all records sharing that fid regardless of class.
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns FID-keyed dict (not class-keyed).
     Kills impl reusing weighted_problem_count_by_class on wrong axis.
  2. Accumulates across ALL records with same fid regardless of class.
     Kills impl that treats (class, fid) pairs as distinct keys.
  3. Empty input -> {} (not raise).
     Kills impl without empty guard.
  4. Unknown severity -> 0.0 contribution (not raise).
     Kills impl raising KeyError on missing severity.
  5. A fid appearing in multiple classes accumulates score correctly.
     Kills impl keyed by (class, fid) instead of just fid.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    weighted_problem_count_by_fid,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_fid_keyed_dict_not_class_keyed() -> None:
    """PRIMARY DISC.: returns fid-keyed dict, not class-keyed.

    Keys must be fid names; class names must not appear.
    Kills impl reusing weighted_problem_count_by_class.
    """
    problems = [
        _p("ClassA", "fid_high", "HIGH"),
        _p("ClassB", "fid_low", "LOW"),
    ]
    weights = {"HIGH": 5.0, "LOW": 1.0}
    result = weighted_problem_count_by_fid(problems, weights)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "fid_high" in result, "fid_high must be present; got " + repr(result)
    assert "fid_low" in result, "fid_low must be present; got " + repr(result)
    assert "ClassA" not in result, "ClassA must NOT be a key; got " + repr(result)
    assert result == {"fid_high": 5.0, "fid_low": 1.0}, (
        "Per-fid totals; got " + repr(result)
    )


def test_accumulates_across_all_records_for_fid() -> None:
    """Fid score accumulates across multiple records.

    fid_x at HIGH(3.0) twice = 6.0.  fid_y at LOW(1.0) = 1.0.
    Kills impl that only counts the first record per fid.
    """
    problems = [
        _p("C1", "fid_x", "HIGH"),
        _p("C2", "fid_x", "HIGH"),
        _p("C3", "fid_y", "LOW"),
    ]
    result = weighted_problem_count_by_fid(problems, {"HIGH": 3.0, "LOW": 1.0})
    assert result == {"fid_x": 6.0, "fid_y": 1.0}, (
        "fid_x=6.0, fid_y=1.0; got " + repr(result)
    )


def test_empty_input_returns_empty_dict() -> None:
    """Empty input -> {} (not raise)."""
    result = weighted_problem_count_by_fid([], {"HIGH": 3.0})
    assert result == {}, "Empty -> {}; got " + repr(result)


def test_unknown_severity_contributes_zero() -> None:
    """Unknown severity contributes 0.0, fid still present in result.

    Kills impl raising KeyError or omitting the fid when weight is 0.
    """
    problems = [
        _p("C1", "fid_known", "HIGH"),
        _p("C2", "fid_unknown", "MYSTERY"),
    ]
    result = weighted_problem_count_by_fid(problems, {"HIGH": 5.0})
    assert "fid_unknown" in result, "fid_unknown must be present; got " + repr(result)
    assert result["fid_unknown"] == 0.0, "MYSTERY -> 0.0; got " + repr(result)


def test_same_fid_across_classes_accumulates() -> None:
    """Same fid in two different classes sums both records' weights.

    Kills impl keyed by (class, fid) pairs instead of just fid.
    """
    problems = [
        _p("ClassA", "shared_fid", "HIGH"),   # 3.0
        _p("ClassB", "shared_fid", "LOW"),    # 1.0
        _p("ClassC", "other_fid", "HIGH"),    # 3.0
    ]
    result = weighted_problem_count_by_fid(problems, {"HIGH": 3.0, "LOW": 1.0})
    assert result["shared_fid"] == 4.0, "3.0+1.0=4.0; got " + repr(result)
    assert result["other_fid"] == 3.0, "3.0; got " + repr(result)
