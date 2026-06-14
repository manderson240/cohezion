"""Item 353: finding_id_overlap_count() -- count of shared finding_ids between two classes (2026-06-08).

``finding_id_overlap_count(problems, class_a, class_b) -> int``:
Returns the count of distinct finding_ids that appear in BOTH class_a and class_b.
Same-class args -> count of that class's distinct finding_ids (self-intersection).
Unknown class -> 0.  Empty -> 0.  Pure; no I/O.

Discriminating tests:

  1. PRIMARY DISC.: returns INTEGER count not a set.
     Kills impl returning frozenset of shared ids.
  2. Correct count: 2 shared finding_ids -> 2.
     Kills impl returning total or per-class count.
  3. Same class for both args -> count of that class's own distinct finding_ids.
     Kills impl returning 0 for self-intersection.
  4. Unknown class returns 0 not an error.
     Kills impl raising KeyError.
  5. Empty problems returns 0.
     Kills impl raising on empty.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    finding_id_overlap_count,
)


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_returns_integer_count_not_set() -> None:
    """Returns int count of shared finding_ids.

    PRIMARY DISCRIMINATOR: kills impl returning frozenset({'F001', 'F002'}).
    alpha and beta share F001, F002 -> 2.
    """
    problems = [
        _p("alpha", "F001"),
        _p("alpha", "F002"),
        _p("beta", "F001"),
        _p("beta", "F002"),
    ]
    result = finding_id_overlap_count(problems, "alpha", "beta")
    assert isinstance(result, int), "Must return int; got " + repr(type(result))
    assert result == 2, "2 shared ids; got " + repr(result)


def test_correct_count_partial_overlap() -> None:
    """Only shared finding_ids counted (not total from either class).

    alpha has F001+F002+F003, beta has F001+F002 -> 2 (not 3 or 5).
    """
    problems = [
        _p("alpha", "F001"),
        _p("alpha", "F002"),
        _p("alpha", "F003"),
        _p("beta", "F001"),
        _p("beta", "F002"),
    ]
    result = finding_id_overlap_count(problems, "alpha", "beta")
    assert result == 2, "2 shared; got " + repr(result)


def test_same_class_both_args_returns_own_count() -> None:
    """Same class for both args -> count of that class's distinct finding_ids.

    Kills impl returning 0 for same-class input.
    alpha has F001+F002 -> self-intersection = 2.
    """
    problems = [_p("alpha", "F001"), _p("alpha", "F002"), _p("beta", "F999")]
    result = finding_id_overlap_count(problems, "alpha", "alpha")
    assert result == 2, "self-intersection = 2; got " + repr(result)


def test_unknown_class_returns_zero() -> None:
    """Unknown class returns 0 without raising KeyError."""
    problems = [_p("alpha", "F001")]
    result = finding_id_overlap_count(problems, "alpha", "UNKNOWN")
    assert result == 0, "unknown class -> 0; got " + repr(result)


def test_empty_input_returns_zero() -> None:
    """Empty problems returns 0."""
    assert finding_id_overlap_count([], "alpha", "beta") == 0
