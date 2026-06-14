"""Item 490: fids_above_score_threshold() -- fid names with score > threshold (2026-06-08).

``fids_above_score_threshold(problems, weights, threshold) -> frozenset[str]``:
Returns frozenset of finding_id strings whose total weighted severity score
STRICTLY exceeds *threshold*.  Fids at exactly threshold are excluded.
Empty problems -> frozenset().  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns FID names (not class names).
     fid_a score=7.0, fid_b score=3.0; threshold=5.0 -> {'fid_a'}.
     Kills impl reusing classes_above_score_threshold (wrong axis).
  2. STRICT inequality: fid at exactly threshold is excluded.
     fid_a score=5.0, threshold=5.0 -> frozenset().
     Kills impl using >= instead of >.
  3. Return type is frozenset.
     Kills impl returning set or list.
  4. Empty problems -> frozenset() (not raise).
     Kills impl without empty-input guard.
  5. Unknown severity contributes 0; fid may stay below threshold.
     Kills impl that raises on missing weight keys.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    fids_above_score_threshold,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_fid_names_not_class_names() -> None:
    """PRIMARY DISC.: keyed by finding_id, not problem_class.

    fid_a: 2xHIGH + 1xLOW = 7.0; fid_b: 1xHIGH = 3.0; threshold=5.0.
    -> frozenset({'fid_a'}).
    Kills impl reusing classes_above_score_threshold (wrong axis).
    """
    problems = [
        _p("ClassA", "fid_a", "HIGH"),
        _p("ClassB", "fid_a", "HIGH"),
        _p("ClassA", "fid_a", "LOW"),
        _p("ClassA", "fid_b", "HIGH"),
    ]
    weights = {"HIGH": 3.0, "LOW": 1.0}
    result = fids_above_score_threshold(problems, weights, 5.0)
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))
    assert result == frozenset({"fid_a"}), "Only fid_a (7.0) > 5.0; got " + repr(result)


def test_strict_inequality_excludes_exact_threshold() -> None:
    """Fid at exactly threshold is NOT included (strict >).

    fid_a score=5.0, threshold=5.0 -> frozenset().
    Kills impl using >= instead of >.
    """
    problems = [
        _p("C", "fid_a", "HIGH"),
        _p("C", "fid_a", "LOW"),  # 3.0 + 2.0 = 5.0 exactly
    ]
    weights = {"HIGH": 3.0, "LOW": 2.0}
    result = fids_above_score_threshold(problems, weights, 5.0)
    assert result == frozenset(), "Score==threshold -> excluded (strict >); got " + repr(result)


def test_return_type_is_frozenset() -> None:
    """Return type is frozenset, not set or list."""
    problems = [_p("C", "fid_x", "HIGH")]
    result = fids_above_score_threshold(problems, {"HIGH": 3.0}, 1.0)
    assert type(result) is frozenset, "Must be frozenset (not set/list); got " + repr(type(result))


def test_empty_problems_returns_empty_frozenset() -> None:
    """Empty problems -> frozenset() (not raise)."""
    result = fids_above_score_threshold([], {"HIGH": 3.0}, 1.0)
    assert result == frozenset(), "Empty -> frozenset(); got " + repr(result)


def test_unknown_severity_contributes_zero_may_stay_below() -> None:
    """Unknown severity contributes 0; fid may stay at or below threshold.

    fid_x has only UNKNOWN_SEV (weight missing); threshold=0.5 -> frozenset().
    Kills impl that raises on missing weight key.
    """
    problems = [_p("C", "fid_x", "UNKNOWN_SEV")]
    result = fids_above_score_threshold(problems, {"HIGH": 3.0}, 0.5)
    assert result == frozenset(), (
        "UNKNOWN_SEV contributes 0 -> fid_x score=0.0 <= 0.5; got " + repr(result)
    )
