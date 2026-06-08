"""Item 324: finding_id_class_map() — inverse index mapping finding_id to set of classes (2026-06-08).

``finding_id_class_map(problems) -> dict[str, frozenset[str]]``:
Returns {finding_id: frozenset_of_class_names_that_contain_it}.
All problems included regardless of severity label.  Empty -> {}.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: value is frozenset (not list) — duplicate class entries impossible.
     Kills impl returning list which could contain repeated class names.
  2. finding_id in exactly one class -> frozenset with exactly one element.
     Kills impl producing empty frozenset or wrong element.
  3. finding_id in multiple classes -> frozenset contains all of those classes.
     Kills impl that only records the first class seen.
  4. Unlabelled problems included (severity does not filter).
     Kills impl filtering out unlabelled problems.
  5. Empty -> {}.
     Kills impl that crashes on empty input.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    finding_id_class_map,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, fid: str, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_value_is_frozenset_not_list() -> None:
    """Value type must be frozenset (not list or set).

    PRIMARY DISCRIMINATOR: kills impl returning a list (which could have duplicates).
    A finding_id appearing 3 times in the same class -> frozenset with 1 element.
    """
    problems = [_ps("alpha", "fid0"), _ps("alpha", "fid0"), _ps("alpha", "fid0")]
    result = finding_id_class_map(problems)
    assert "fid0" in result, "fid0 must be in result; got " + repr(result)
    val = result["fid0"]
    assert isinstance(val, frozenset), (
        "value must be frozenset; got " + repr(type(val))
    )
    assert val == frozenset({"alpha"}), (
        "fid0 in alpha only -> frozenset({'alpha'}); got " + repr(val)
    )


def test_finding_id_in_one_class_gives_singleton_frozenset() -> None:
    """finding_id in exactly one class -> frozenset with one element.

    Kills impl producing empty frozenset or extra elements.
    """
    problems = [_ps("alpha", "fid1", "HIGH"), _ps("beta", "fid2")]
    result = finding_id_class_map(problems)
    assert result.get("fid1") == frozenset({"alpha"}), (
        "fid1 only in alpha -> frozenset({'alpha'}); got " + repr(result.get("fid1"))
    )
    assert result.get("fid2") == frozenset({"beta"}), (
        "fid2 only in beta -> frozenset({'beta'}); got " + repr(result.get("fid2"))
    )


def test_finding_id_in_multiple_classes_contains_all_classes() -> None:
    """finding_id in 3 classes -> frozenset of all 3 class names.

    Kills impl that only records the first class seen.
    """
    problems = [
        _ps("alpha", "shared"),
        _ps("beta", "shared"),
        _ps("gamma", "shared"),
    ]
    result = finding_id_class_map(problems)
    assert result.get("shared") == frozenset({"alpha", "beta", "gamma"}), (
        "shared fid in 3 classes -> frozenset with 3 names; got " + repr(result.get("shared"))
    )


def test_unlabelled_problems_included() -> None:
    """Problems with severity='' are included in the map.

    Kills impl that filters out unlabelled problems.
    alpha: 1 unlabelled problem with fid0 -> fid0 must be in result.
    """
    problems = [_ps("alpha", "fid0", "")]
    result = finding_id_class_map(problems)
    assert "fid0" in result, "unlabelled problem fid0 must be in result; got " + repr(result)
    assert result["fid0"] == frozenset({"alpha"}), (
        "unlabelled fid0 -> frozenset({'alpha'}); got " + repr(result["fid0"])
    )


def test_empty_input_returns_empty_dict() -> None:
    """Empty input -> {} without raising.

    Kills impl that crashes on empty list.
    """
    result = finding_id_class_map([])
    assert result == {}, "empty -> {}; got " + repr(result)
