"""Item 384: top_n_finding_ids_by_count() -- top N finding_ids by record count (2026-06-08).

``top_n_finding_ids_by_count(problems, n) -> list[str]``:
Returns a list of at most n finding_id strings sorted descending by total
occurrence count across all classes.  Ties broken lexicographically ascending.
n=0 -> [].  Empty problems -> [].  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: uses finding_id axis (not class name axis).
     Kills impl delegating to top_n_classes_by_count.
  2. Descending count, not ascending.
     Kills impl that sorts ascending.
  3. Ties broken lexicographically ascending.
     Kills impl with non-deterministic ties.
  4. Returns at most n entries.
     Kills impl returning all finding_ids.
  5. n=0 returns [] and empty input returns [].
     Kills impl raising on 0 or crashing on empty.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    top_n_finding_ids_by_count,
)


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_uses_finding_id_axis_not_class() -> None:
    """Uses finding_id counts, not class name counts.

    PRIMARY DISCRIMINATOR: kills impl delegating to top_n_classes_by_count.
    fid:0 appears 3 times, fid:1 appears 2 times, fid:2 appears 1 time.
    """
    problems = [
        _p("a", "fid:0"),
        _p("b", "fid:0"),
        _p("c", "fid:0"),
        _p("a", "fid:1"),
        _p("b", "fid:1"),
        _p("a", "fid:2"),
    ]
    result = top_n_finding_ids_by_count(problems, 3)
    assert result == ["fid:0", "fid:1", "fid:2"], "Descending fid:0>fid:1>fid:2; got " + repr(
        result
    )


def test_descending_by_count_not_ascending() -> None:
    """Returns finding_ids sorted descending by count.

    Kills impl sorting ascending.
    most frequent fid must be first.
    """
    problems = [
        _p("x", "common"),
        _p("y", "common"),
        _p("z", "common"),
        _p("x", "rare"),
    ]
    result = top_n_finding_ids_by_count(problems, 2)
    assert len(result) == 2, "n=2 -> 2 results; got " + repr(result)
    assert result[0] == "common", "most common first; got " + repr(result[0])
    assert result[1] == "rare", "rare is second; got " + repr(result[1])


def test_ties_broken_lexicographically_ascending() -> None:
    """Tied finding_ids sorted ascending lexicographically.

    Kills impl with non-deterministic tie-breaking.
    a-fid and b-fid both appear twice — a-fid must come first.
    """
    problems = [
        _p("cls1", "b-fid"),
        _p("cls2", "b-fid"),
        _p("cls1", "a-fid"),
        _p("cls2", "a-fid"),
        _p("cls3", "z-fid"),
    ]
    result = top_n_finding_ids_by_count(problems, 2)
    assert len(result) == 2
    assert result[0] == "a-fid", "a-fid < b-fid lexicographically; got " + repr(result[0])
    assert result[1] == "b-fid", "b-fid is second; got " + repr(result[1])


def test_returns_at_most_n_entries() -> None:
    """Returns at most n entries even when more finding_ids exist.

    Kills impl returning all finding_ids.
    """
    problems = [_p("cls", f"fid:{i}") for i in range(10)]
    result = top_n_finding_ids_by_count(problems, 4)
    assert len(result) == 4, "n=4 -> 4 results; got " + repr(len(result))
    assert all(isinstance(f, str) for f in result), "Must return strings"


def test_n_zero_and_empty_return_empty() -> None:
    """n=0 returns [] and empty problems returns []."""
    problems = [_p("a", "f:0"), _p("b", "f:1")]
    assert top_n_finding_ids_by_count(problems, 0) == [], "n=0 -> []"
    assert top_n_finding_ids_by_count([], 5) == [], "empty -> []"
