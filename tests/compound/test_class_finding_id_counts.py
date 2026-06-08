"""Item 323: class_finding_id_counts() — distinct finding_id count per class (2026-06-08).

``class_finding_id_counts(problems) -> dict[str, int]``:
Returns {class: count_of_distinct_finding_ids_in_that_class}.
A finding_id appearing in N records within a class still counts as 1.
All problems included regardless of severity label.  Empty -> {}.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: count = distinct finding_ids, NOT total problem records.
     Kills impl counting records (not unique finding_ids).
  2. Same finding_id across multiple classes does NOT inflate either class's count.
     Kills impl using a global set instead of per-class sets.
  3. All severity labels included (labelled AND unlabelled).
     Kills impl filtering out unlabelled problems.
  4. Empty -> {}.
     Kills impl crashing on empty list.
  5. Class with one problem -> count = 1.
     Kills impl with off-by-one (minimum case).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_finding_id_counts,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, fid: str, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_count_is_distinct_finding_ids_not_record_count() -> None:
    """count = distinct finding_ids per class, NOT number of Problem records.

    PRIMARY DISCRIMINATOR: kills impl counting records.
    alpha: 5 records all with finding_id='alpha:0' -> count = 1 (not 5).
    """
    problems = [_ps("alpha", "alpha:0") for _ in range(5)]
    result = class_finding_id_counts(problems)
    assert result.get("alpha") == 1, "alpha: 5 records with same fid -> count=1; got " + repr(
        result.get("alpha")
    )


def test_shared_finding_id_does_not_inflate_class_counts() -> None:
    """A finding_id in both alpha and beta counts independently per class.

    Kills impl using a global set (would give 1 total but 0 for each class).
    alpha: fids {a0, a1}. beta: fid {a0} (shared with alpha) -> beta count = 1.
    """
    problems = [
        _ps("alpha", "a0"),
        _ps("alpha", "a1"),
        _ps("beta", "a0"),  # a0 also in alpha, but counts as 1 for beta
    ]
    result = class_finding_id_counts(problems)
    assert result.get("alpha") == 2, "alpha: a0+a1 -> count=2; got " + repr(result.get("alpha"))
    assert result.get("beta") == 1, "beta: a0 only -> count=1; got " + repr(result.get("beta"))


def test_unlabelled_problems_included_in_count() -> None:
    """Unlabelled problems (severity='') are included; no severity filter.

    Kills impl that ignores problems with severity=''.
    alpha: 2 problems, both unlabelled but distinct finding_ids -> count = 2.
    """
    problems = [
        _ps("alpha", "a0", ""),
        _ps("alpha", "a1", ""),
    ]
    result = class_finding_id_counts(problems)
    assert result.get("alpha") == 2, "alpha: 2 unlabelled distinct fids -> count=2; got " + repr(
        result.get("alpha")
    )


def test_empty_input_returns_empty_dict() -> None:
    """Empty input -> {} without raising.

    Kills impl that crashes on empty list.
    """
    result = class_finding_id_counts([])
    assert result == {}, "empty -> {}; got " + repr(result)


def test_single_problem_class_has_count_one() -> None:
    """Class with exactly one problem -> count = 1 (minimum case).

    Kills impl with off-by-one or initialising counts at 0.
    """
    problems = [_ps("alpha", "a0")]
    result = class_finding_id_counts(problems)
    assert result == {"alpha": 1}, "Single problem -> {alpha: 1}; got " + repr(result)
