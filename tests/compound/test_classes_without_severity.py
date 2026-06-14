"""Item 292: classes_without_severity() — classes with ZERO labelled problems (2026-06-08).

``classes_without_severity(problems: list[Problem]) -> frozenset[str]``:
Returns frozenset of class names where ALL problems have severity=''.
A class with even ONE labelled problem is excluded.  Empty -> frozenset().
Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: class with at least one labelled problem is NOT in result.
     Kills impl returning all classes regardless of labelling.
  2. Class with mixed labelled/unlabelled problems is excluded.
     Kills impl that includes classes with ANY unlabelled problems.
  3. Empty input -> frozenset().
     Kills impl raising on empty.
  4. Return type is frozenset[str].
     Kills impl returning list or set.
  5. Class where ALL problems are unlabelled IS in result.
     Kills impl that never includes any class (over-filters).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    classes_without_severity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_labelled_class_excluded() -> None:
    """A class with at least one labelled problem is NOT in the result.

    PRIMARY DISCRIMINATOR: kills impl that returns all classes.
    'has_label' has one HIGH problem -> NOT in result.
    'all_unlabelled' has only severity='' -> IS in result.
    """
    problems = [
        _ps("has_label", 0, "HIGH"),
        _p("all_unlabelled", 1),  # severity=""
        _p("all_unlabelled", 2),  # severity=""
    ]
    result = classes_without_severity(problems)
    assert "has_label" not in result, "'has_label' has a labelled problem -> excluded; got " + repr(
        result
    )
    assert "all_unlabelled" in result, (
        "'all_unlabelled' is entirely unlabelled -> included; got " + repr(result)
    )


def test_mixed_class_excluded() -> None:
    """Class with mixed labelled and unlabelled problems is excluded.

    Kills impl that includes classes with ANY unlabelled problems.
    'mixed' has one HIGH and one unlabelled -> NOT in result.
    """
    problems = [
        _ps("mixed", 0, "HIGH"),
        _p("mixed", 1),  # severity=""
    ]
    result = classes_without_severity(problems)
    assert "mixed" not in result, "'mixed' has 1 labelled problem -> excluded; got " + repr(result)


def test_empty_input_returns_empty_frozenset() -> None:
    """Empty input -> frozenset() without raising.

    Kills impl raising on empty list.
    """
    result = classes_without_severity([])
    assert result == frozenset(), "Empty input -> frozenset(); got " + repr(result)


def test_return_type_is_frozenset() -> None:
    """Return type is frozenset[str].

    Kills impl returning mutable set or list.
    """
    problems = [_p("alpha", 0)]
    result = classes_without_severity(problems)
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))


def test_all_unlabelled_class_included() -> None:
    """Class where every problem is unlabelled IS in result.

    Kills impl that never includes any class (over-filters).
    'only_unlabelled' has 3 problems all with severity='' -> in result.
    """
    problems = [
        _p("only_unlabelled", 0),
        _p("only_unlabelled", 1),
        _p("only_unlabelled", 2),
        _ps("labelled", 3, "LOW"),
    ]
    result = classes_without_severity(problems)
    assert "only_unlabelled" in result, (
        "'only_unlabelled' has 3 unlabelled problems -> in result; got " + repr(result)
    )
    assert len(result) == 1, "Only 1 fully-unlabelled class; got " + repr(result)
