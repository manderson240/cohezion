"""Item 485: all_fid_severity_scores() -- total severity score for every fid (2026-06-08).

``all_fid_severity_scores(problems, weights) -> dict[str, float]``:
Returns dict[finding_id -> total_severity_score] for every fid in problems.
Symmetric to all_severity_scores on the fid axis.  Fids with score=0.0
still appear (non-sparse by fid).  Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: dict keyed by fid (not class).
     fid_a score=7.0, fid_b score=3.0 -> {'fid_a': 7.0, 'fid_b': 3.0}.
     Kills impl reusing all_severity_scores (wrong axis -- keyed by class).
  2. Weighted sum not count.
     fid_a: HIGH x2 weight=3.0 + LOW x1 weight=1.0 -> 7.0, not 3.
     Kills impl returning plain count per fid.
  3. Fid present even if score=0.0 (all unknown severities).
     Kills impl omitting zero-score fids.
  4. Empty problems -> {}.
     Kills impl with unguarded access.
  5. Unknown severity contributes 0 (not raise).
     Kills impl raising KeyError.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    all_fid_severity_scores,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_dict_keyed_by_fid_not_class() -> None:
    """PRIMARY DISC.: dict keyed by fid, not class.

    fid_a score=7.0, fid_b score=3.0.
    Kills impl reusing all_severity_scores (keyed by class).
    """
    problems = [
        _p("ClassA", "fid_a", "HIGH"),
        _p("ClassB", "fid_a", "HIGH"),
        _p("ClassC", "fid_a", "LOW"),
        _p("ClassA", "fid_b", "HIGH"),
    ]
    weights = {"HIGH": 3.0, "LOW": 1.0}
    result = all_fid_severity_scores(problems, weights)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert result.get("fid_a") == 7.0, "fid_a=7.0; got " + repr(result)
    assert result.get("fid_b") == 3.0, "fid_b=3.0; got " + repr(result)
    assert "ClassA" not in result, "Keys must be fids not classes; got " + repr(result)


def test_score_is_weighted_sum_not_count() -> None:
    """Weighted sum not count."""
    problems = [
        _p("ClassA", "fid_a", "HIGH"),
        _p("ClassA", "fid_a", "HIGH"),
        _p("ClassA", "fid_a", "LOW"),
    ]
    result = all_fid_severity_scores(problems, {"HIGH": 3.0, "LOW": 1.0})
    assert result["fid_a"] == 7.0, "7.0 not 3; got " + repr(result)


def test_zero_score_fid_still_present() -> None:
    """Fid with only unknown severities -> score=0.0 but still present."""
    problems = [
        _p("ClassA", "fid_a", "UNKNOWN"),
        _p("ClassB", "fid_b", "HIGH"),
    ]
    result = all_fid_severity_scores(problems, {"HIGH": 5.0})
    assert "fid_a" in result, "fid_a must appear even with 0.0; got " + repr(result)
    assert result["fid_a"] == 0.0, "fid_a score=0.0; got " + repr(result)


def test_empty_problems_returns_empty_dict() -> None:
    """Empty problems -> {}."""
    result = all_fid_severity_scores([], {"HIGH": 3.0})
    assert result == {}, "Empty -> {}; got " + repr(result)


def test_unknown_severity_contributes_zero() -> None:
    """Unknown severity contributes 0 (not raise)."""
    problems = [
        _p("ClassA", "fid_a", "HIGH"),
        _p("ClassA", "fid_a", "MYSTERY"),
    ]
    result = all_fid_severity_scores(problems, {"HIGH": 4.0})
    assert result["fid_a"] == 4.0, "MYSTERY contributes 0; got " + repr(result)
