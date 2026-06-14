"""Item 285: finding_ids_by_class() — class to frozenset of finding_ids inverse index (2026-06-08).

``finding_ids_by_class(problems: list[Problem]) -> dict[str, frozenset[str]]``:
Returns {class_name: frozenset(p.finding_id for p in class)} for every class
present. Empty input -> {}. Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: values are frozensets of finding_ids, not counts or lists.
     Kills impl returning {class: count} or {class: list}.
  2. Each class maps to ALL finding_ids in that class.
     Kills impl returning only first or last finding_id per class.
  3. Empty input -> {}.
     Kills impl raising on empty.
  4. Finding_id appearing twice in one class appears once in the frozenset.
     Verifies set semantics (frozenset deduplicates).
  5. Return type is dict with frozenset values.
     Kills impl using plain set or list as values.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    finding_ids_by_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_values_are_frozensets_of_finding_ids() -> None:
    """Values are frozensets of finding_ids, not counts or lists.

    PRIMARY DISCRIMINATOR: kills impl returning {class: count} or {class: list}.
    """
    problems = [_p("alpha", "a1"), _p("alpha", "a2"), _p("beta", "b1")]
    result = finding_ids_by_class(problems)
    assert isinstance(result.get("alpha"), frozenset), "Values must be frozenset; got " + repr(
        type(result.get("alpha"))
    )
    assert result["alpha"] == frozenset({"a1", "a2"}), (
        "alpha must have frozenset({'a1','a2'}); got " + repr(result["alpha"])
    )


def test_all_finding_ids_included_per_class() -> None:
    """Each class maps to ALL of its finding_ids.

    Kills impl returning only the first or last finding_id.
    """
    problems = [_p("alpha", f"a{i}") for i in range(5)] + [_p("beta", "b1")]
    result = finding_ids_by_class(problems)
    expected_alpha = frozenset({f"a{i}" for i in range(5)})
    assert result["alpha"] == expected_alpha, "All 5 alpha ids must be present; got " + repr(
        result["alpha"]
    )
    assert result["beta"] == frozenset({"b1"}), "beta must have frozenset({'b1'}); got " + repr(
        result["beta"]
    )


def test_empty_input_returns_empty_dict() -> None:
    """Empty input -> {}.

    Kills impl raising on empty input.
    """
    result = finding_ids_by_class([])
    assert result == {}, "Empty input -> {}; got " + repr(result)


def test_duplicate_finding_id_in_class_deduplicated() -> None:
    """Duplicate finding_id in one class appears once in frozenset.

    Verifies set semantics (frozenset deduplicates by definition).
    """
    problems = [_p("alpha", "same"), _p("alpha", "same")]
    result = finding_ids_by_class(problems)
    assert result["alpha"] == frozenset({"same"}), (
        "Duplicate id -> appears once in frozenset; got " + repr(result["alpha"])
    )


def test_return_type_is_dict_with_frozenset_values() -> None:
    """Return is dict[str, frozenset[str]], not dict[str, list[str]] or dict[str, set[str]].

    Kills impl using plain set or list as values.
    """
    problems = [_p("alpha", "a1")]
    result = finding_ids_by_class(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    for v in result.values():
        assert isinstance(v, frozenset), "All values must be frozenset; got " + repr(type(v))
