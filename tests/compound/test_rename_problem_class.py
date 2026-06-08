"""Item 183: rename_problem_class() — safe non-destructive rename (2026-06-08).

``rename_problem_class(problems: list[Problem], old_class: str, new_class: str)``
→ ``list[Problem]``:
Returns a new list where every finding with ``problem_class == old_class``
has its class rewritten to ``new_class``.  Findings with other classes are
returned unchanged.  ``finding_id`` prefixes are NOT rewritten — IDs remain
stable across the rename.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: matching class renamed, others untouched.
     Kills an impl that renames EVERY finding's class (ignoring old_class).
  2. ``old_class`` absent → list returned unchanged.
     Kills an impl that always modifies every element.
  3. Empty list → ``[]`` (no raises).
     Kills an impl that raises on empty input.
  4. ``finding_id`` prefixes NOT rewritten (IDs remain stable).
     Kills an impl that also rewrites finding_id strings (breaks stable-id contract).
  5. Returned list is a new list, not the same object (pure / non-destructive).
     Kills an impl that mutates the input list in-place.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    rename_problem_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_matching_class_renamed_others_untouched() -> None:
    """Old class renamed; other classes return unchanged.

    PRIMARY DISCRIMINATOR: kills an impl that renames every finding
    regardless of problem_class (ignores the old_class argument).
    """
    problems = [_p("complexity_outlier"), _p("nesting_outlier"), _p("complexity_outlier", 1)]

    result = rename_problem_class(problems, "complexity_outlier", "cyclomatic_complexity")

    renamed = [p for p in result if p.problem_class == "cyclomatic_complexity"]
    unchanged = [p for p in result if p.problem_class == "nesting_outlier"]

    assert len(renamed) == 2, f"Two 'complexity_outlier' findings must be renamed; got {renamed!r}"
    assert len(unchanged) == 1, f"'nesting_outlier' must be unchanged; got {unchanged!r}"
    assert len(result) == 3, f"Total count must equal input count; got {len(result)}"


def test_absent_class_returns_unchanged_list() -> None:
    """old_class not in problems → list content returned unchanged.

    Kills an impl that always modifies every element regardless of match.
    """
    problems = [_p("nesting_outlier"), _p("long_function")]

    result = rename_problem_class(problems, "complexity_outlier", "cyclomatic_complexity")

    assert all(p.problem_class != "cyclomatic_complexity" for p in result), (
        f"No class should be renamed when old_class is absent; got {result!r}"
    )
    assert len(result) == 2, f"List length must not change; got {len(result)}"


def test_empty_list_returns_empty() -> None:
    """Empty list → [] (no raises).

    Kills an impl that raises IndexError or similar on empty input.
    """
    result = rename_problem_class([], "complexity_outlier", "cyclomatic_complexity")

    assert result == [], f"Empty input must return []; got {result!r}"


def test_finding_id_not_rewritten() -> None:
    """finding_id prefixes are NOT rewritten — IDs remain stable.

    Kills an impl that also rewrites the problem_class prefix inside
    finding_id strings, which would break the stable-id contract and
    corrupt downstream diffs.
    """
    original_fid = "complexity_outlier:src/foo.py:10"
    problems = [Problem(problem_class="complexity_outlier", finding_id=original_fid)]

    result = rename_problem_class(problems, "complexity_outlier", "cyclomatic_complexity")

    assert len(result) == 1
    assert result[0].problem_class == "cyclomatic_complexity", (
        f"problem_class must be updated; got {result[0].problem_class!r}"
    )
    assert result[0].finding_id == original_fid, (
        f"finding_id must NOT be rewritten; got {result[0].finding_id!r}"
    )


def test_returns_new_list_not_mutated_in_place() -> None:
    """Returned list is a new object (pure / non-destructive).

    Kills an impl that mutates the input list in-place, which would break
    the pure function contract and cause subtle aliasing bugs.
    """
    problems = [_p("complexity_outlier")]

    result = rename_problem_class(problems, "complexity_outlier", "cyclomatic_complexity")

    assert result is not problems, "rename_problem_class must return a new list, not mutate input"
    # Input must be unchanged
    assert problems[0].problem_class == "complexity_outlier", (
        f"Input list must not be mutated; got {problems[0].problem_class!r}"
    )
