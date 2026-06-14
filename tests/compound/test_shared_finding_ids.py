"""Item 287: shared_finding_ids() — frozenset of finding_ids shared across 2+ classes (2026-06-08).

``shared_finding_ids(problems: list[Problem]) -> frozenset[str]``:
Returns frozenset of finding_ids that appear under AT LEAST two distinct
problem_class values. Finding_ids that appear in only one class are excluded.
Empty or all-unique → frozenset(). Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: id appearing in only one class is NOT in the result.
     Kills impl returning all finding_ids (like finding_ids_by_class values).
  2. id appearing in two distinct classes IS in the result.
     Kills impl that requires ≥3 classes (too strict).
  3. Empty input -> frozenset().
     Kills impl raising on empty.
  4. Return type is frozenset[str], not list or set.
     Kills impl returning a mutable set or list.
  5. Complement property: shared_finding_ids ∩ any unique_class frozenset == ∅.
     Verifies exact complementarity with finding_ids_unique_to_class.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    finding_ids_unique_to_class,
    shared_finding_ids,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_exclusive_id_not_in_shared() -> None:
    """A finding_id in only one class is NOT shared.

    PRIMARY DISCRIMINATOR: kills impl returning all finding_ids.
    'only_alpha' appears in alpha only -> not in shared_finding_ids.
    """
    problems = [
        _p("alpha", "only_alpha"),
        _p("alpha", "shared"),
        _p("beta", "shared"),
    ]
    result = shared_finding_ids(problems)
    assert "only_alpha" not in result, "'only_alpha' is in alpha only -> not shared; got " + repr(
        result
    )


def test_id_in_two_classes_is_shared() -> None:
    """A finding_id appearing in exactly two classes is in the result.

    Kills impl requiring ≥3 classes.
    """
    problems = [
        _p("alpha", "shared"),
        _p("beta", "shared"),
    ]
    result = shared_finding_ids(problems)
    assert "shared" in result, (
        "'shared' appears in alpha and beta -> in shared_finding_ids; got " + repr(result)
    )


def test_empty_input_returns_empty_frozenset() -> None:
    """Empty input -> frozenset().

    Kills impl raising on empty input.
    """
    result = shared_finding_ids([])
    assert result == frozenset(), "Empty input -> frozenset(); got " + repr(result)


def test_return_type_is_frozenset() -> None:
    """Return type is frozenset[str], not list or plain set.

    Kills impl returning a mutable set or list.
    """
    problems = [_p("alpha", "a1"), _p("beta", "a1")]
    result = shared_finding_ids(problems)
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))


def test_complement_of_unique_to_class() -> None:
    """shared_finding_ids ∩ any class's unique frozenset must be empty.

    Verifies exact complementarity: a shared id can never appear as exclusive.
    """
    problems = [
        _p("alpha", "shared"),
        _p("alpha", "only_alpha"),
        _p("beta", "shared"),
        _p("beta", "only_beta"),
        _p("gamma", "only_gamma"),
    ]
    shared = shared_finding_ids(problems)
    unique_by_class = finding_ids_unique_to_class(problems)
    for cls, exclusive in unique_by_class.items():
        overlap = shared & exclusive
        assert overlap == frozenset(), (
            f"Class {cls!r}: shared ids {shared!r} overlap with exclusive {exclusive!r}: "
            f"intersection {overlap!r}"
        )
