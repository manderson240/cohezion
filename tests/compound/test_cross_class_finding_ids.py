"""Item 325: cross_class_finding_ids() — finding_ids shared across ≥2 classes (2026-06-08).

``cross_class_finding_ids(problems) -> frozenset[str]``:
Returns frozenset of finding_ids that appear in at least 2 distinct classes.
A finding_id in the same class N times is still in only 1 class (excluded).
Empty -> frozenset().  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: ONLY finding_ids in ≥2 distinct classes included.
     Kills impl including single-class fids.
  2. finding_id in same class N times = 1 class (excluded from result).
     Kills impl counting record occurrences instead of distinct classes.
  3. finding_id in exactly 2 classes IS included.
     Kills impl requiring ≥3 classes (off-by-one on threshold).
  4. Return type is frozenset (not list or set).
     Kills impl with mutable return type.
  5. Empty -> frozenset() (not {}).
     Kills impl returning empty dict instead of empty frozenset.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    cross_class_finding_ids,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_only_fids_in_two_or_more_classes_included() -> None:
    """Only finding_ids in >= 2 distinct classes are in the result.

    PRIMARY DISCRIMINATOR: kills impl including single-class fids.
    fid0: alpha only -> excluded.
    fid1: alpha AND beta -> included.
    """
    problems = [
        _ps("alpha", "fid0"),
        _ps("alpha", "fid1"),
        _ps("beta", "fid1"),
    ]
    result = cross_class_finding_ids(problems)
    assert "fid1" in result, "fid1 in alpha+beta -> included; got " + repr(result)
    assert "fid0" not in result, "fid0 in alpha only -> excluded; got " + repr(result)


def test_fid_in_same_class_multiple_times_excluded() -> None:
    """finding_id in same class N times = 1 class = excluded.

    Kills impl counting records instead of distinct classes.
    fid0: alpha × 5 records -> 1 class -> excluded.
    """
    problems = [_ps("alpha", "fid0") for _ in range(5)]
    result = cross_class_finding_ids(problems)
    assert "fid0" not in result, "fid0 in alpha×5 but only 1 class -> excluded; got " + repr(result)


def test_fid_in_exactly_two_classes_is_included() -> None:
    """finding_id in exactly 2 distinct classes meets the threshold (≥2).

    Kills impl using > 2 threshold (off-by-one).
    shared: alpha + beta (exactly 2 classes) -> included.
    """
    problems = [_ps("alpha", "shared"), _ps("beta", "shared")]
    result = cross_class_finding_ids(problems)
    assert "shared" in result, "shared in exactly 2 classes -> included; got " + repr(result)


def test_return_type_is_frozenset() -> None:
    """Return type must be frozenset (not list or set).

    Kills impl returning mutable set or list.
    """
    problems = [_ps("alpha", "fid0"), _ps("beta", "fid0")]
    result = cross_class_finding_ids(problems)
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))


def test_empty_input_returns_empty_frozenset() -> None:
    """Empty input -> frozenset() (not {} or []).

    Kills impl returning empty dict.
    """
    result = cross_class_finding_ids([])
    assert result == frozenset(), "empty -> frozenset(); got " + repr(result)
    assert isinstance(result, frozenset), "Must be frozenset; got " + repr(type(result))
