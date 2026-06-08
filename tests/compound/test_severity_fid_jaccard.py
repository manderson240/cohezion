"""Item 446: severity_fid_jaccard() -- Jaccard similarity of two severity fid sets (2026-06-08).

``severity_fid_jaccard(problems, severity_a, severity_b) -> float``:
Returns |fids_a INTERSECT fids_b| / |fids_a UNION fids_b|.
0.0 if union empty.  Result in [0.0, 1.0].  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: Jaccard formula applied to severity-filtered fid sets
     (not class sets -- kills impl reusing fid_class_jaccard on wrong axis).
     Two severities sharing all fids -> 1.0.
  2. No overlap -> 0.0 (not raise).
     Validates denominator guard and empty-intersection handling.
  3. Both empty/unknown -> 0.0 (not raise, no ZeroDivisionError).
     Kills impl with unguarded division.
  4. Same severity queried twice -> 1.0 (J(A,A) = 1).
     Validates self-similarity = 1.0.
  5. Partial overlap -> correct Jaccard value in (0, 1).
     Validates core formula against counting heuristics.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_fid_jaccard,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_jaccard_on_severity_fid_sets_not_class() -> None:
    """PRIMARY DISC.: Jaccard over severity-filtered fid sets, not class sets.

    HIGH fids={f1,f2}, LOW fids={f2,f3}.
    J = |{f2}| / |{f1,f2,f3}| = 1/3.
    Kills impl reusing fid_class_jaccard on class field.
    """
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f2", "LOW"),
        _p("c", "f3", "LOW"),
    ]
    result = severity_fid_jaccard(problems, "HIGH", "LOW")
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    expected = 1 / 3
    assert abs(result - expected) < 1e-9, "J=1/3; got " + repr(result)


def test_no_overlap_returns_zero() -> None:
    """Disjoint fid sets -> Jaccard = 0.0."""
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "LOW"),
    ]
    result = severity_fid_jaccard(problems, "HIGH", "LOW")
    assert abs(result - 0.0) < 1e-9, f"Disjoint -> 0.0; got {result!r}"


def test_empty_returns_zero() -> None:
    """Empty input -> 0.0 (no ZeroDivisionError)."""
    result = severity_fid_jaccard([], "HIGH", "LOW")
    assert result == 0.0, f"Empty -> 0.0; got {result!r}"
    assert isinstance(result, float)


def test_same_severity_returns_one() -> None:
    """J(A, A) = 1.0 (self-similarity)."""
    problems = [_p("c", "f1", "HIGH"), _p("c", "f2", "HIGH")]
    result = severity_fid_jaccard(problems, "HIGH", "HIGH")
    assert abs(result - 1.0) < 1e-9, f"Same severity -> 1.0; got {result!r}"


def test_partial_overlap_correct_jaccard() -> None:
    """Partial overlap returns the correct Jaccard coefficient.

    HIGH fids={f1,f2,f3}, LOW fids={f2,f3,f4}.
    Intersection={f2,f3}, Union={f1,f2,f3,f4}.
    J = 2/4 = 0.5.
    """
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f3", "HIGH"),
        _p("c", "f2", "LOW"),
        _p("c", "f3", "LOW"),
        _p("c", "f4", "LOW"),
    ]
    result = severity_fid_jaccard(problems, "HIGH", "LOW")
    assert abs(result - 0.5) < 1e-9, f"J=0.5; got {result!r}"
