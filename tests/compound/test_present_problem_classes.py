"""Item 184: present_problem_classes() — watchlist intersection query (2026-06-08).

``present_problem_classes(problems: list[Problem], classes: frozenset[str])``
→ ``frozenset[str]``:
Returns the subset of *classes* that appear at least once in *problems*.
Empty *classes* → ``frozenset()``.  Empty *problems* → ``frozenset()``.
Pure; no I/O.

Enables "which of these N watchlist classes fired today?" queries::

    fired = present_problem_classes(findings, frozenset({"production_assert", "complexity_outlier"}))

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: non-empty overlap → frozenset of only the WATCHLIST classes present.
     Kills an impl that returns ALL classes found in problems instead of the
     intersection with *classes* (i.e. returns problem_count_by_class keys instead).
  2. No overlap → frozenset() (empty).
     Kills an impl that always returns the full *classes* argument.
  3. Empty *classes* → frozenset() (no raises).
     Kills an impl that returns the full set of problem classes from *problems*.
  4. Empty *problems* → frozenset() (no raises).
     Kills an impl that raises IndexError on empty input.
  5. Partial overlap → only the intersecting class returned.
     Kills an impl that returns all classes from *classes* regardless of presence.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    present_problem_classes,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_overlap_returns_only_watchlist_present_classes() -> None:
    """Some watchlist classes present → only those returned (not all problem classes).

    PRIMARY DISCRIMINATOR: kills an impl that returns ALL distinct problem_class
    values from problems instead of restricting to the watchlist *classes*.
    'long_function' is in problems but NOT in *classes* — it must NOT appear in result.
    """
    problems = [_p("complexity_outlier"), _p("nesting_outlier"), _p("long_function")]

    result = present_problem_classes(
        problems, frozenset({"complexity_outlier", "production_assert"})
    )

    assert result == frozenset({"complexity_outlier"}), (
        f"Only watchlist classes present in problems must be returned; got {result!r}"
    )


def test_no_overlap_returns_empty_frozenset() -> None:
    """No watchlist class appears in problems → frozenset().

    Kills an impl that always returns the full *classes* argument.
    """
    problems = [_p("long_function"), _p("nesting_outlier")]

    result = present_problem_classes(
        problems, frozenset({"complexity_outlier", "production_assert"})
    )

    assert result == frozenset(), f"No overlap must return frozenset(); got {result!r}"


def test_empty_classes_returns_empty_frozenset() -> None:
    """Empty *classes* watchlist → frozenset() (nothing to intersect).

    Kills an impl that returns the set of distinct problem classes from *problems*
    when *classes* is empty.
    """
    problems = [_p("complexity_outlier"), _p("nesting_outlier")]

    result = present_problem_classes(problems, frozenset())

    assert result == frozenset(), f"Empty classes must return frozenset(); got {result!r}"


def test_empty_problems_returns_empty_frozenset() -> None:
    """Empty *problems* → frozenset() (no raises).

    Kills an impl that raises IndexError or similar on empty input.
    """
    result = present_problem_classes([], frozenset({"complexity_outlier"}))

    assert result == frozenset(), f"Empty problems must return frozenset(); got {result!r}"


def test_partial_overlap_returns_only_matching_class() -> None:
    """Watchlist has two classes but only one appears in problems → that one returned.

    Kills an impl that returns all classes from *classes* regardless of whether
    they appear in *problems* (i.e. returns the watchlist instead of the intersection).
    """
    problems = [_p("complexity_outlier", i) for i in range(5)]  # only complexity_outlier

    result = present_problem_classes(problems, frozenset({"complexity_outlier", "nesting_outlier"}))

    assert result == frozenset({"complexity_outlier"}), (
        f"Only 'complexity_outlier' fires; 'nesting_outlier' must be absent; got {result!r}"
    )
