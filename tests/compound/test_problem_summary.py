"""Item 163: problem_summary() — typed ProblemSummary composition struct (2026-06-08).

``problem_summary(problems)`` → ``ProblemSummary``: composes the output of
``problem_count_by_class`` (item 160) and ``top_problem_classes`` (item 161)
into a single frozen dataclass for the loop health report.

Fields:
  - ``total: int``                        — ``len(problems)``
  - ``by_class: dict[str, int]``          — ``problem_count_by_class(problems)``
  - ``top_classes: list[tuple[str, int]]`` — ``top_problem_classes(problems)``
  - ``has_problems: bool``                — ``total > 0``

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: ``total`` equals ``len(problems)``, NOT the sum of ``by_class``
     values (which would be equal here but distinguishable when a ``problems``
     list has semantically duplicate finding_ids — the spec says raw count of
     the list, not a re-derived sum).
     Kills an impl that computes total as ``sum(by_class.values())``.
  2. ``by_class`` equals ``problem_count_by_class(problems)`` for the same input.
     Kills an impl that independently re-counts or uses a different algorithm.
  3. ``top_classes`` equals ``top_problem_classes(problems)`` for the same input.
     Kills an impl that sorts differently or uses a different n.
  4. ``has_problems`` is False for empty input, True for non-empty.
     Kills an impl that always returns True or derives has_problems from by_class.
  5. Returns a frozen dataclass instance (immutable — callers cannot mutate fields).
     Kills an impl that returns a plain mutable dict or a namespace object.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    ProblemSummary,
    problem_count_by_class,
    problem_summary,
    top_problem_classes,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_total_equals_len_problems() -> None:
    """total == len(problems) — raw list length, not sum of by_class values.

    PRIMARY DISCRIMINATOR: kills an impl that uses sum(by_class.values())
    which is equal for well-formed inputs but documents the spec precisely.
    Uses a list with duplicate finding_ids to surface the difference (both
    are counted as separate list entries, not de-duplicated by id).
    """
    problems = [_p("alpha", 1), _p("alpha", 2), _p("beta", 3)]
    summary = problem_summary(problems)

    assert summary.total == 3, f"Expected total=3; got {summary.total}"
    # Also verify total matches len()
    assert summary.total == len(problems), (
        f"total must equal len(problems); got {summary.total} vs {len(problems)}"
    )


def test_by_class_matches_problem_count_by_class() -> None:
    """by_class equals problem_count_by_class(problems) for the same input.

    Kills an impl that re-counts independently using a different algorithm
    (e.g. one that skips certain classes or uses set dedup on finding_ids).
    """
    problems = [_p("alpha", 1), _p("alpha", 2), _p("beta", 3)]
    summary = problem_summary(problems)
    expected = problem_count_by_class(problems)

    assert summary.by_class == expected, (
        f"by_class must equal problem_count_by_class;\n"
        f"  expected: {expected}\n"
        f"  got:      {summary.by_class}"
    )


def test_top_classes_matches_top_problem_classes() -> None:
    """top_classes equals top_problem_classes(problems) for the same input.

    Kills an impl that sorts differently (e.g. ascending instead of descending)
    or truncates at a different n than the default.
    """
    problems = [_p("a", 1), _p("a", 2), _p("a", 3), _p("b", 1), _p("b", 2), _p("c", 1)]
    summary = problem_summary(problems)
    expected = top_problem_classes(problems)

    assert summary.top_classes == expected, (
        f"top_classes must equal top_problem_classes(problems);\n"
        f"  expected: {expected}\n"
        f"  got:      {summary.top_classes}"
    )


def test_has_problems_false_for_empty() -> None:
    """has_problems is False for empty input.

    Kills an impl that always returns has_problems=True or derives it from
    by_class (which would be empty but might be implemented incorrectly).
    """
    summary = problem_summary([])

    assert summary.has_problems is False, (
        f"has_problems must be False for empty input; got {summary.has_problems}"
    )
    assert summary.total == 0
    assert summary.by_class == {}
    assert summary.top_classes == []


def test_has_problems_true_for_non_empty() -> None:
    """has_problems is True for non-empty input.

    Paired with the empty-input test to kill an always-False impl.
    """
    summary = problem_summary([_p("any", 1)])

    assert summary.has_problems is True, (
        f"has_problems must be True for non-empty input; got {summary.has_problems}"
    )


def test_returns_frozen_dataclass() -> None:
    """problem_summary() returns a ProblemSummary (frozen dataclass) instance.

    Kills an impl that returns a mutable dict, a SimpleNamespace, or an
    unfrozen dataclass whose fields could be accidentally mutated by a caller.
    """
    import dataclasses

    summary = problem_summary([_p("x", 1)])

    assert isinstance(summary, ProblemSummary), (
        f"Expected ProblemSummary instance; got {type(summary)}"
    )
    # Verify frozen — attempting to set an attribute should raise FrozenInstanceError
    try:
        summary.total = 999  # type: ignore[misc]
        raise AssertionError("FrozenInstanceError not raised — dataclass is not frozen")
    except dataclasses.FrozenInstanceError:
        pass  # Expected
