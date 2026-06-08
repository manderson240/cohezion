"""Item 315: unique_finding_ids_across_classes() — finding_ids in exactly 1 class (2026-06-08).

``unique_finding_ids_across_classes(problems) -> frozenset[str]``:
Returns frozenset of finding_ids that appear in exactly one distinct class.
Finding_ids appearing in ≥2 classes are excluded (they're shared).
A finding_id with multiple records all in the same class IS in result (still 1 class).
Empty -> frozenset().  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: only finding_ids in EXACTLY 1 class included.
     Kills impl including shared finding_ids (those in ≥2 classes).
  2. Finding_id in same class multiple times IS in result (1 class, many records).
     Kills impl requiring exactly 1 record.
  3. Finding_id in 2 different classes NOT in result.
     Kills impl using total record count rather than distinct class count.
  4. Return type is frozenset[str].
     Kills impl returning list or set.
  5. Empty problems -> frozenset().
     Kills impl raising on empty input.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    unique_finding_ids_across_classes,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def _ps(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_only_single_class_fids_included() -> None:
    """Only finding_ids appearing in exactly 1 distinct class are in result.

    PRIMARY DISCRIMINATOR: kills impl including shared finding_ids.
    fid='A': only alpha -> in result.
    fid='B': alpha + beta -> NOT in result (shared).
    """
    problems = [
        _p("alpha", "A"),
        _p("alpha", "B"),
        _p("beta", "B"),  # B is shared between alpha and beta
    ]
    result = unique_finding_ids_across_classes(problems)
    assert "A" in result, "fid A only in alpha -> in result; got " + repr(result)
    assert "B" not in result, "fid B in alpha+beta -> NOT in result; got " + repr(result)


def test_multiple_records_same_class_still_in_result() -> None:
    """Finding_id in same class multiple times: still exactly 1 class -> in result.

    Kills impl requiring exactly 1 record.
    fid='C': 3 records all in alpha -> 1 distinct class -> in result.
    """
    problems = [_p("alpha", "C"), _p("alpha", "C"), _ps("alpha", "C", "HIGH")]
    result = unique_finding_ids_across_classes(problems)
    assert "C" in result, (
        "fid C has 3 records but all in alpha -> 1 class -> in result; got " + repr(result)
    )


def test_two_class_fid_not_in_result() -> None:
    """Finding_id appearing in exactly 2 classes is NOT in result.

    Kills impl using total record count rather than distinct class count.
    fid='D': alpha + beta (same record or different) -> 2 classes -> NOT in result.
    """
    problems = [_p("alpha", "D"), _p("beta", "D")]
    result = unique_finding_ids_across_classes(problems)
    assert "D" not in result, "fid D in 2 classes -> NOT in result; got " + repr(result)


def test_return_type_is_frozenset() -> None:
    """Return type is frozenset[str].

    Kills impl returning list or mutable set.
    """
    problems = [_p("alpha", "E")]
    result = unique_finding_ids_across_classes(problems)
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))
    assert "E" in result


def test_empty_problems_returns_frozenset() -> None:
    """Empty problems -> frozenset() without raising.

    Kills impl raising on empty input.
    """
    result = unique_finding_ids_across_classes([])
    assert result == frozenset(), "Empty -> frozenset(); got " + repr(result)
