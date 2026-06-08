"""Item 186: merge_problems() — order-preserving union of two finding lists (2026-06-08).

``merge_problems(a: list[Problem], b: list[Problem])`` → ``list[Problem]``:
Returns all findings from *a* first, then findings from *b* whose
``finding_id`` was not already in *a*.  Equivalent to
``deduplicate_problems(a + b)`` but documents the merge semantics explicitly.
Empty lists handled gracefully.  Pure; no I/O.

Enables parallel scanning::

    merged = merge_problems(run_a, run_b)

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: a + b merged, b-duplicate dropped → a first then new b.
     Kills an impl that returns only *a* or only *b* (ignoring the other list).
  2. b-finding duplicating a-finding dropped from result.
     Kills an impl that keeps both (concatenation without deduplication).
  3. Both empty → [] (no raises).
     Kills an impl that raises on empty input.
  4. a empty → b's findings returned.
     Kills an impl that always returns *a*.
  5. b empty → a's findings returned unchanged.
     Kills an impl that always returns *b*.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    merge_problems,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_a_first_then_new_from_b() -> None:
    """All of a comes first; b findings not in a are appended.

    PRIMARY DISCRIMINATOR: kills an impl that returns only *a* (ignores *b*)
    or only *b* (ignores *a*), or that returns them in the wrong order.
    """
    a = [_p("cls", "id_a1"), _p("cls", "id_a2")]
    b = [_p("cls", "id_b1"), _p("cls", "id_b2")]

    result = merge_problems(a, b)

    assert len(result) == 4, f"All 4 unique IDs must appear; got {len(result)}: {result!r}"
    # a's findings come first, in order
    assert result[0].finding_id == "id_a1"
    assert result[1].finding_id == "id_a2"
    # then b's findings (neither duplicated a)
    assert result[2].finding_id == "id_b1"
    assert result[3].finding_id == "id_b2"


def test_b_duplicate_of_a_is_dropped() -> None:
    """b-finding with same finding_id as an a-finding is dropped.

    Kills an impl that concatenates without deduplication (returns a + b
    even when b contains findings already in a).
    """
    shared_id = "complexity_outlier:src/foo.py:10"
    a = [_p("complexity_outlier", shared_id)]
    b = [_p("complexity_outlier", shared_id), _p("nesting_outlier", "nesting_outlier:bar.py:3")]

    result = merge_problems(a, b)

    assert len(result) == 2, f"Duplicate must be dropped; expected 2, got {len(result)}: {result!r}"
    assert result[0].finding_id == shared_id
    assert result[1].finding_id == "nesting_outlier:bar.py:3"


def test_both_empty_returns_empty() -> None:
    """Both lists empty → [] (no raises).

    Kills an impl that raises on empty input.
    """
    result = merge_problems([], [])

    assert result == [], f"Both empty must return []; got {result!r}"


def test_a_empty_returns_b_findings() -> None:
    """a is empty → b's findings are returned.

    Kills an impl that always returns *a* (would return []).
    """
    b = [_p("cls", "id_b1"), _p("cls", "id_b2")]

    result = merge_problems([], b)

    assert len(result) == 2, f"b's findings must be returned; got {result!r}"
    assert result[0].finding_id == "id_b1"
    assert result[1].finding_id == "id_b2"


def test_b_empty_returns_a_findings() -> None:
    """b is empty → a's findings are returned unchanged.

    Kills an impl that always returns *b* (would return []).
    """
    a = [_p("cls", "id_a1"), _p("cls", "id_a2")]

    result = merge_problems(a, [])

    assert len(result) == 2, f"a's findings must be returned; got {result!r}"
    assert result[0].finding_id == "id_a1"
    assert result[1].finding_id == "id_a2"
