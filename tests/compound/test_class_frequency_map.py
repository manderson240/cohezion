"""Item 198: class_frequency_map() — insertion-stable frequency dict (2026-06-08).

``class_frequency_map(problems: list[Problem])`` → ``dict[str, int]``:
Returns ``{problem_class: count}`` where keys are ordered by FIRST OCCURRENCE
in *problems* (CPython 3.7+ dict insertion-order guarantee).
Empty list → ``{}``.  Pure; no I/O.

Makes the insertion-order key guarantee explicit (``problem_count_by_class``
also preserves it, but the name doesn't advertise it)::

    freq = class_frequency_map(findings)
    list(freq.keys())  # classes in first-occurrence order

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: dict keys are in first-occurrence order (not alphabetical).
     Kills an impl that sorts keys alphabetically.
  2. Values equal the count for each class.
     Kills an impl that returns 1 for every class regardless.
  3. Empty list → {} (no raises).
     Kills an impl that raises on empty input.
  4. Single-class input → {cls: n}.
     Kills an impl that returns {} for single-class input.
  5. Unknown class has no entry (no zero-count phantom keys).
     Kills an impl that pre-populates all template classes with 0.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_frequency_map,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_keys_in_first_occurrence_order() -> None:
    """Dict keys are in first-occurrence order (not alphabetically sorted).

    PRIMARY DISCRIMINATOR: kills an impl that sorts keys alphabetically
    (which would return ["alpha", "beta"] instead of ["beta", "alpha"]).
    'beta' appears before 'alpha' in insertion order; it must be first key.
    """
    problems = [
        _p("beta", 0),
        _p("alpha", 0),
        _p("beta", 1),
        _p("alpha", 1),
    ]

    result = class_frequency_map(problems)

    keys = list(result.keys())
    assert keys == ["beta", "alpha"], (
        f"Keys must be in first-occurrence order (beta→alpha); got {keys!r}"
    )


def test_values_equal_counts() -> None:
    """Each value equals the number of findings for that class.

    Kills an impl that returns 1 for every class (ignoring true frequency).
    """
    problems = [
        _p("complexity_outlier", 0),
        _p("nesting_outlier"),
        _p("complexity_outlier", 1),
        _p("complexity_outlier", 2),
    ]

    result = class_frequency_map(problems)

    assert result["complexity_outlier"] == 3, (
        f"complexity_outlier count must be 3; got {result.get('complexity_outlier')!r}"
    )
    assert result["nesting_outlier"] == 1, (
        f"nesting_outlier count must be 1; got {result.get('nesting_outlier')!r}"
    )


def test_empty_list_returns_empty_dict() -> None:
    """Empty list → {} (no raises).

    Kills an impl that raises IndexError or returns a dict with phantom keys.
    """
    result = class_frequency_map([])

    assert result == {}, f"Empty input must return {{}}; got {result!r}"


def test_single_class_returns_single_entry() -> None:
    """All findings share one class → {cls: n} with n = len(problems).

    Kills an impl that returns {} for single-class input.
    """
    problems = [_p("long_function", i) for i in range(4)]

    result = class_frequency_map(problems)

    assert result == {"long_function": 4}, (
        f"Single-class with 4 findings must return {{'long_function': 4}}; got {result!r}"
    )


def test_absent_class_has_no_entry() -> None:
    """A class not in problems has no key in the result dict.

    Kills an impl that pre-populates all known template classes with count=0
    instead of only including classes that appear in the input.
    """
    problems = [_p("complexity_outlier")]

    result = class_frequency_map(problems)

    assert "nesting_outlier" not in result, (
        f"'nesting_outlier' must not appear (not in input); got {result!r}"
    )
    assert len(result) == 1, f"Only one class in result; got {result!r}"
