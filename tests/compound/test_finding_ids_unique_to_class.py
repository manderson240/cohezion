"""Item 286: finding_ids_unique_to_class() — finding_ids exclusive to one class (2026-06-08).

``finding_ids_unique_to_class(problems: list[Problem]) -> dict[str, frozenset[str]]``:
Returns {class: frozenset(finding_ids that appear in ONLY this class)} for every
class. Finding_ids that appear in 2+ classes are excluded from ALL classes' frozensets.
Empty input -> {}. Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: shared finding_ids excluded from both classes.
     Kills impl returning finding_ids_by_class() without the exclusion filter.
  2. Class-exclusive ids appear in the correct class only.
     Verifies the exclusion is selective (non-shared ids retained).
  3. Empty input -> {}.
     Kills impl raising on empty.
  4. Class with NO exclusive ids gets empty frozenset (not omitted from dict).
     Kills impl that skips classes with no exclusive ids.
  5. Return type is dict with frozenset values.
     Kills impl returning lists or plain sets.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    finding_ids_unique_to_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_shared_ids_excluded_from_all_classes() -> None:
    """Shared finding_id appears in NEITHER class's frozenset.

    PRIMARY DISCRIMINATOR: kills impl that includes shared ids (finding_ids_by_class).
    'shared' appears in both alpha and beta -> excluded from both.
    """
    problems = [
        _p("alpha", "shared"),
        _p("alpha", "only_alpha"),
        _p("beta", "shared"),
        _p("beta", "only_beta"),
    ]
    result = finding_ids_unique_to_class(problems)
    assert "shared" not in result["alpha"], (
        "'shared' appears in both classes -> excluded from alpha; got " + repr(result["alpha"])
    )
    assert "shared" not in result["beta"], (
        "'shared' appears in both classes -> excluded from beta; got " + repr(result["beta"])
    )


def test_exclusive_ids_appear_in_correct_class() -> None:
    """Class-exclusive ids are retained in their class's frozenset.

    Verifies the filter is selective (only shared ids removed).
    """
    problems = [
        _p("alpha", "shared"),
        _p("alpha", "only_alpha"),
        _p("beta", "shared"),
        _p("beta", "only_beta"),
    ]
    result = finding_ids_unique_to_class(problems)
    assert result["alpha"] == frozenset({"only_alpha"}), (
        "only_alpha exclusive to alpha; got " + repr(result["alpha"])
    )
    assert result["beta"] == frozenset({"only_beta"}), (
        "only_beta exclusive to beta; got " + repr(result["beta"])
    )


def test_empty_input_returns_empty_dict() -> None:
    """Empty input -> {}.

    Kills impl raising on empty input.
    """
    result = finding_ids_unique_to_class([])
    assert result == {}, "Empty input -> {}; got " + repr(result)


def test_class_with_no_exclusive_ids_has_empty_frozenset() -> None:
    """A class with ALL its finding_ids shared gets empty frozenset, not omission.

    Kills impl omitting classes with no exclusive ids.
    """
    problems = [
        _p("alpha", "shared_1"),
        _p("alpha", "shared_2"),
        _p("beta", "shared_1"),
        _p("beta", "shared_2"),
        _p("beta", "exclusive"),
    ]
    result = finding_ids_unique_to_class(problems)
    assert "alpha" in result, "alpha must appear even with no exclusive ids"
    assert result["alpha"] == frozenset(), (
        "alpha has no exclusive ids -> empty frozenset; got " + repr(result["alpha"])
    )


def test_return_type_is_dict_with_frozenset_values() -> None:
    """Return type is dict[str, frozenset[str]].

    Kills impl using lists or plain sets as values.
    """
    problems = [_p("alpha", "a1"), _p("beta", "b1")]
    result = finding_ids_unique_to_class(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    for v in result.values():
        assert isinstance(v, frozenset), (
            "Values must be frozenset; got " + repr(type(v))
        )
