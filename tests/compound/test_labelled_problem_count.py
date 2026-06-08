"""Item 266: labelled_problem_count() — count of problems with a severity label (2026-06-08).

``labelled_problem_count(problems: list[Problem]) -> int``:
Returns the count of problems where ``p.severity != ""``.  Empty input or
all-unlabelled → ``0``.  Equals ``len(problems) - len(problems_without_severity(problems))``.
Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: counts labelled problems not total problems.
     Kills impl returning len(problems) (includes unlabelled).
  2. 0 when all problems are unlabelled.
     Kills impl returning len(problems) when some are unlabelled.
  3. 0 on empty input.
     Kills impl that raises on empty.
  4. Equal to len(problems) - len(problems_without_severity(problems)).
     Verifies complement relationship.
  5. Return type is int.
     Kills impl returning float or a list.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    labelled_problem_count,
    problems_without_severity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


def _unlab(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_counts_labelled_not_total() -> None:
    """Counts problems with non-empty severity, not all problems.

    PRIMARY DISCRIMINATOR: kills impl returning len(problems).
    3 labelled + 2 unlabelled → count = 3, not 5.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "LOW"),
        _ps("alpha", 2, "CRITICAL"),
        _unlab("beta", 0),
        _unlab("beta", 1),
    ]
    result = labelled_problem_count(problems)
    assert result == 3, "3 labelled + 2 unlabelled → count=3 (not 5); got " + repr(result)


def test_zero_when_all_unlabelled() -> None:
    """0 when all problems have severity=''.

    Kills impl returning len(problems) even when some unlabelled.
    """
    problems = [_unlab("alpha", i) for i in range(4)]
    result = labelled_problem_count(problems)
    assert result == 0, "All unlabelled → 0; got " + repr(result)


def test_zero_on_empty_input() -> None:
    """Empty input → 0.

    Kills impl raising on empty input.
    """
    result = labelled_problem_count([])
    assert result == 0, "Empty → 0; got " + repr(result)


def test_complement_relationship() -> None:
    """labelled_problem_count + len(problems_without_severity) == len(problems).

    Verifies the complement identity.
    """
    problems = [
        _ps("a", 0, "HIGH"), _ps("a", 1, "LOW"),
        _unlab("b", 0), _unlab("b", 1), _unlab("b", 2),
    ]
    labelled = labelled_problem_count(problems)
    unlabelled = len(problems_without_severity(problems))
    assert labelled + unlabelled == len(problems), (
        "labelled + unlabelled must equal total; got "
        + repr((labelled, unlabelled, len(problems)))
    )


def test_return_type_is_int() -> None:
    """Return type is int.

    Kills impl returning float.
    """
    result = labelled_problem_count([_ps("alpha", 0, "HIGH")])
    assert isinstance(result, int), "Must return int; got " + repr(type(result))
    assert result == 1
