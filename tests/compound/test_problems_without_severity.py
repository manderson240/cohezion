"""Item 265: problems_without_severity() — problems with no severity label (2026-06-08).

``problems_without_severity(problems: list[Problem]) -> list[Problem]``:
Returns all :class:`Problem` instances whose ``severity`` is the empty string
``""``, in input order.  Empty input or all-labelled scan → ``[]``.
Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: filters to severity=="" only.
     Kills impl that returns problems with ANY non-None severity (including
     non-empty strings), i.e. the inverse of the correct filter.
  2. Preserves input order among returned problems.
     Kills impl sorting by finding_id.
  3. Empty list when all problems have non-empty severity.
     Kills impl returning all problems when no unlabelled ones exist.
  4. Empty list on empty input.
     Kills impl raising on empty.
  5. Returns list[Problem] not a count.
     Kills impl returning len(unlabelled).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
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


def test_returns_only_unlabelled_not_labelled() -> None:
    """Filters to severity=="" only; excludes labelled problems.

    PRIMARY DISCRIMINATOR: kills impl returning labelled problems.
    u0, u1 are unlabelled; p0 is labelled HIGH → only u0 and u1 returned.
    """
    u0 = _unlab("alpha", 0)
    p0 = _ps("alpha", 1, "HIGH")
    u1 = _unlab("beta", 0)
    result = problems_without_severity([u0, p0, u1])
    assert result == [u0, u1], "Only unlabelled problems; got " + repr(result)


def test_preserves_input_order() -> None:
    """Unlabelled problems returned in input order.

    Kills impl sorting by finding_id or class.
    """
    u2 = _unlab("alpha", 2)
    u0 = _unlab("alpha", 0)
    u1 = _unlab("alpha", 1)
    problems = [u2, _ps("beta", 0, "LOW"), u0, u1]
    result = problems_without_severity(problems)
    assert result == [u2, u0, u1], "Order must match input; got " + repr(result)


def test_all_labelled_returns_empty_list() -> None:
    """Empty list when all problems have non-empty severity.

    Kills impl returning all problems.
    """
    problems = [_ps("alpha", i, "HIGH") for i in range(5)]
    result = problems_without_severity(problems)
    assert result == [], "All labelled → []; got " + repr(result)


def test_empty_input_returns_empty_list() -> None:
    """Empty input → [].

    Kills impl raising on empty input.
    """
    result = problems_without_severity([])
    assert result == [], "Empty input → []; got " + repr(result)


def test_returns_problem_instances_not_count() -> None:
    """Returns list[Problem] not a count int.

    Kills impl returning len(unlabelled_problems).
    """
    u = _unlab("alpha", 0)
    result = problems_without_severity([u, _ps("beta", 0, "HIGH")])
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert len(result) == 1 and result[0] is u
