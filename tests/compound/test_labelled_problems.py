"""Item 344: labelled_problems() — filter to problems with non-empty severity (2026-06-08).

``labelled_problems(problems) -> list[Problem]``:
Returns only Problem objects where severity != ''.
Complement of unlabelled_problems.  Empty input -> [].  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns Problem objects not severity strings.
     Kills impl returning severity labels.
  2. Unlabelled problems (severity='') are excluded.
     Kills impl returning all problems.
  3. Original insertion order preserved.
     Kills impl that reorders.
  4. Empty input returns [].
     Kills impl raising on empty.
  5. All-unlabelled input returns [].
     Kills impl returning some problems on all-unlabelled.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    labelled_problems,
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


def test_returns_problem_objects_not_strings() -> None:
    """Returns Problem instances, not severity strings.

    PRIMARY DISCRIMINATOR: kills impl returning ['HIGH', 'LOW'] instead of Problems.
    """
    problems = [_ps("alpha", 0, "HIGH"), _p("beta", 0)]
    result = labelled_problems(problems)
    assert len(result) == 1
    assert isinstance(result[0], Problem), "Must return Problem objects"
    assert result[0].finding_id == "alpha:0"


def test_unlabelled_excluded() -> None:
    """Problems with severity='' are excluded.

    Kills impl returning all problems.
    3 labelled + 2 unlabelled -> 3 returned.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _p("beta", 0),
        _ps("alpha", 1, "LOW"),
        _p("beta", 1),
        _ps("gamma", 0, "CRITICAL"),
    ]
    result = labelled_problems(problems)
    assert len(result) == 3, "3 labelled -> 3 returned; got " + repr(len(result))
    assert all(p.severity != "" for p in result), "All returned must be labelled"


def test_original_order_preserved() -> None:
    """Returned problems maintain original insertion order.

    Kills impl that sorts.
    """
    problems = [
        _ps("z", 0, "LOW"), _p("a", 0), _ps("m", 0, "HIGH"), _ps("a", 0, "CRITICAL"),
    ]
    result = labelled_problems(problems)
    assert [p.finding_id for p in result] == ["z:0", "m:0", "a:0"], (
        "Order preserved; got " + repr([p.finding_id for p in result])
    )


def test_empty_input_returns_empty_list() -> None:
    """Empty input returns [] without raising."""
    assert labelled_problems([]) == []


def test_all_unlabelled_returns_empty_list() -> None:
    """All-unlabelled input returns [].

    Kills impl returning some problems on all-unlabelled input.
    """
    problems = [_p("alpha", i) for i in range(5)]
    result = labelled_problems(problems)
    assert result == [], "all unlabelled -> []; got " + repr(result)
