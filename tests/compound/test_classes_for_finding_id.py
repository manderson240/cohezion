"""Item 338: classes_for_finding_id() — frozenset of classes sharing a finding ID (2026-06-08).

``classes_for_finding_id(problems, finding_id) -> frozenset[str]``:
Inverse of finding_ids_for_class.  Returns all class names that have at least one
Problem record with the given finding_id.  Unknown finding_id -> frozenset().
Empty input -> frozenset().  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns class names, not finding_ids (not the identity function).
     Kills impl returning the finding_id itself.
  2. Multiple classes sharing the same finding_id are all returned.
     Kills impl returning only the first class seen.
  3. Unknown finding_id returns frozenset() (not KeyError).
     Kills impl raising on missing key.
  4. Empty input returns frozenset().
     Kills impl raising on empty.
  5. Only classes with the EXACT finding_id are returned (no substring match).
     Kills impl doing substring or prefix matching.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    classes_for_finding_id,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_class_names_not_finding_id() -> None:
    """Returns problem_class values, not the finding_id itself.

    PRIMARY DISCRIMINATOR: kills impl that returns {finding_id} as identity.
    finding_id='F001' -> returns {'alpha'}, not {'F001'}.
    """
    problems = [_p("alpha", "F001"), _p("beta", "F002")]
    result = classes_for_finding_id(problems, "F001")
    assert result == frozenset({"alpha"}), (
        "F001 belongs to alpha -> {'alpha'}; got " + repr(result)
    )
    assert "F001" not in result, "result must not contain the finding_id itself"


def test_multiple_classes_for_same_finding_id() -> None:
    """All classes sharing a finding_id are returned.

    Kills impl returning only the first class seen.
    F001 appears in alpha AND beta -> both returned.
    """
    problems = [_p("alpha", "F001"), _p("beta", "F001"), _p("gamma", "F002")]
    result = classes_for_finding_id(problems, "F001")
    assert result == frozenset({"alpha", "beta"}), (
        "F001 in alpha+beta -> frozenset({'alpha','beta'}); got " + repr(result)
    )


def test_unknown_finding_id_returns_empty_frozenset() -> None:
    """Unknown finding_id returns frozenset() without raising.

    Kills impl raising KeyError on missing ID.
    """
    problems = [_p("alpha", "F001")]
    result = classes_for_finding_id(problems, "UNKNOWN_ID")
    assert result == frozenset(), "unknown ID -> frozenset(); got " + repr(result)


def test_empty_input_returns_empty_frozenset() -> None:
    """Empty input returns frozenset() without raising."""
    result = classes_for_finding_id([], "F001")
    assert result == frozenset(), "empty -> frozenset(); got " + repr(result)


def test_exact_match_only_no_substring() -> None:
    """Only exact finding_id match is returned, not substring.

    Kills impl doing substring or prefix matching.
    'F0' should not match 'F001'.
    """
    problems = [_p("alpha", "F001"), _p("beta", "F0")]
    result = classes_for_finding_id(problems, "F0")
    assert result == frozenset({"beta"}), (
        "exact 'F0' matches only beta, not alpha('F001'); got " + repr(result)
    )
