"""Item 430: fid_class_jaccard() — Jaccard similarity between two classes on the fid axis (2026-06-08).

``fid_class_jaccard(problems, class_a, class_b) -> float``:
Returns |fids_a ∩ fids_b| / |fids_a ∪ fids_b|.
1.0 = identical fid sets.  0.0 = disjoint or either class absent.
Empty -> 0.0.  class_a == class_b -> 1.0.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: formula is intersection/union (not intersection alone).
     Two classes with 2 shared + 1 exclusive each -> J=2/4=0.5.
     Kills impl returning just the count or fraction of class_a.
  2. Identical fid sets -> 1.0.
     Validates perfect-similarity edge case.
  3. Disjoint fid sets -> 0.0.
     Validates zero-similarity edge case.
  4. class_a == class_b -> 1.0.
     Kills impl that computes union incorrectly for self-comparison.
  5. Empty -> 0.0 (not ZeroDivisionError).
     Kills impl with unguarded division.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    fid_class_jaccard,
)


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_intersection_over_union_formula() -> None:
    """Returns |fids_a ∩ fids_b| / |fids_a ∪ fids_b|.

    PRIMARY DISCRIMINATOR: kills impl returning just intersection count.
    fids_a={shared1,shared2,only_a}, fids_b={shared1,shared2,only_b}.
    intersection=2, union=4 -> J=0.5.
    """
    problems = [
        _p("class_a", "shared1"),
        _p("class_a", "shared2"),
        _p("class_a", "only_a"),
        _p("class_b", "shared1"),
        _p("class_b", "shared2"),
        _p("class_b", "only_b"),
    ]
    result = fid_class_jaccard(problems, "class_a", "class_b")
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert abs(result - 0.5) < 1e-9, "J=2/4=0.5; got " + repr(result)


def test_identical_fid_sets_returns_one() -> None:
    """Classes with identical fid sets -> J = 1.0."""
    problems = [
        _p("alpha", "F001"),
        _p("alpha", "F002"),
        _p("beta", "F001"),
        _p("beta", "F002"),
    ]
    result = fid_class_jaccard(problems, "alpha", "beta")
    assert abs(result - 1.0) < 1e-9, "Identical fid sets -> 1.0; got " + repr(result)


def test_disjoint_fid_sets_returns_zero() -> None:
    """Completely disjoint fid sets -> J = 0.0."""
    problems = [
        _p("alpha", "F001"),
        _p("beta", "F002"),
    ]
    result = fid_class_jaccard(problems, "alpha", "beta")
    assert abs(result - 0.0) < 1e-9, "Disjoint -> 0.0; got " + repr(result)


def test_same_class_returns_one() -> None:
    """class_a == class_b -> J = 1.0 (self-similarity)."""
    problems = [_p("alpha", "F001"), _p("alpha", "F002")]
    result = fid_class_jaccard(problems, "alpha", "alpha")
    assert abs(result - 1.0) < 1e-9, "Same class -> 1.0; got " + repr(result)


def test_empty_returns_zero() -> None:
    """Empty input returns 0.0, not ZeroDivisionError."""
    result = fid_class_jaccard([], "alpha", "beta")
    assert result == 0.0, "Empty -> 0.0; got " + repr(result)
    assert isinstance(result, float)
