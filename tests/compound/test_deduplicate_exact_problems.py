"""Item 361: deduplicate_exact_problems() — dedup by all 3 fields (2026-06-08).

``deduplicate_exact_problems(problems) -> list[Problem]``:
Returns a new list with duplicate Problem records removed; "duplicate" means all 3
fields (problem_class, finding_id, severity) match a previously-seen record.  Keeps
the FIRST occurrence; insertion order of unique records is preserved.
Empty input → [].  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: same class+finding_id but DIFFERENT severity is NOT a duplicate.
     Kills impl deduplicating by (class, finding_id) only or finding_id only.
  2. Exact duplicate (all 3 fields identical) is dropped; first occurrence kept.
     Kills impl keeping last occurrence.
  3. Insertion order of unique elements is preserved.
     Kills impl returning sorted or hash-ordered results.
  4. Empty input returns [].
     Kills impl raising on empty.
  5. All unique records → list unchanged (length invariant).
     Kills impl that drops non-duplicates.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    deduplicate_exact_problems,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_different_severity_not_a_duplicate() -> None:
    """same class+finding_id but different severity → both kept.

    PRIMARY DISCRIMINATOR: kills impl deduplicating by (class, finding_id) only.
    """
    p1 = Problem(problem_class="alpha", finding_id="alpha:0", severity="HIGH")
    p2 = Problem(problem_class="alpha", finding_id="alpha:0", severity="CRITICAL")
    result = deduplicate_exact_problems([p1, p2])
    assert len(result) == 2, "Different severity = distinct identity; got " + repr(result)
    assert result[0] is p1
    assert result[1] is p2


def test_exact_duplicate_dropped_first_kept() -> None:
    """All 3 fields identical → second occurrence dropped; first kept.

    Kills impl keeping last occurrence.
    """
    p = _p("beta", 0, "LOW")
    dup = Problem(problem_class="beta", finding_id="beta:0", severity="LOW")
    result = deduplicate_exact_problems([p, dup, _p("gamma", 0)])
    assert result[0] is p, "First occurrence kept; got " + repr(result[0])
    assert len(result) == 2, "Duplicate dropped; got " + repr(len(result))


def test_insertion_order_preserved() -> None:
    """Unique elements come out in original insertion order.

    Kills impl returning sorted or hash-ordered results.
    """
    problems = [_p("c", 0), _p("a", 0), _p("b", 0)]
    result = deduplicate_exact_problems(problems)
    assert [p.problem_class for p in result] == ["c", "a", "b"], (
        "Insertion order preserved; got " + repr([p.problem_class for p in result])
    )


def test_empty_input_returns_empty() -> None:
    """Empty input returns [] without raising."""
    assert deduplicate_exact_problems([]) == []


def test_all_unique_length_unchanged() -> None:
    """No duplicates → output length equals input length.

    Kills impl that drops non-duplicates.
    """
    problems = [_p("a", 0, "HIGH"), _p("a", 0, "LOW"), _p("b", 0)]
    result = deduplicate_exact_problems(problems)
    assert len(result) == 3, "All unique; got " + repr(len(result))
