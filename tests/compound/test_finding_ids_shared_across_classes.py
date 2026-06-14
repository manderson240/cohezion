"""Item 386: finding_ids_shared_across_classes() — finding_ids in ≥2 classes (2026-06-08).

``finding_ids_shared_across_classes(problems) -> frozenset[str]``:
Returns the frozenset of finding_id strings that appear under at least 2
distinct problem_class values.  A finding_id present in only one class is
excluded even if it has many records.  Empty → frozenset().  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: finding_id must appear in ≥2 DISTINCT CLASSES, not ≥2 records.
     Kills impl counting records instead of distinct classes.
  2. Single-class scan → frozenset() (no cross-class fids).
     Kills impl including single-class fids.
  3. Returns frozenset not list (unordered, deduplicated).
     Kills impl returning list[str].
  4. Empty input returns frozenset().
     Kills impl raising on empty.
  5. Finding_id in exactly 2 classes is included; in only 1 class is excluded.
     Kills impl using > 2 threshold or including all fids.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    finding_ids_shared_across_classes,
)


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_requires_distinct_classes_not_record_count() -> None:
    """Finding_id must appear in ≥2 DISTINCT classes, not just ≥2 records.

    PRIMARY DISCRIMINATOR: kills impl counting records instead of classes.
    fid:multi is in alpha+beta (2 classes) → included.
    fid:solo is in alpha only, 3 times → excluded.
    """
    problems = [
        _p("alpha", "fid:multi"),
        _p("beta", "fid:multi"),
        _p("alpha", "fid:solo"),
        _p("alpha", "fid:solo"),
        _p("alpha", "fid:solo"),
    ]
    result = finding_ids_shared_across_classes(problems)
    assert "fid:multi" in result, "fid:multi is in 2 classes → included; got " + repr(result)
    assert "fid:solo" not in result, "fid:solo is in 1 class only → excluded; got " + repr(result)


def test_single_class_scan_returns_empty() -> None:
    """All problems in one class → frozenset() since no cross-class fids.

    Kills impl including single-class fids.
    """
    problems = [_p("only-class", f"fid:{i}") for i in range(5)]
    result = finding_ids_shared_across_classes(problems)
    assert result == frozenset(), "single class → no cross-class fids; got " + repr(result)


def test_returns_frozenset_not_list() -> None:
    """Returns frozenset, not list.

    Kills impl returning list[str].
    """
    problems = [_p("a", "shared"), _p("b", "shared")]
    result = finding_ids_shared_across_classes(problems)
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))
    assert all(isinstance(v, str) for v in result), "Elements must be str"


def test_empty_input_returns_empty_frozenset() -> None:
    """Empty input returns frozenset()."""
    assert finding_ids_shared_across_classes([]) == frozenset()


def test_exactly_two_classes_included_one_class_excluded() -> None:
    """Finding_id in exactly 2 classes is included; in 1 class is excluded.

    Kills impl using > 2 threshold.
    """
    problems = [
        _p("cls1", "two-classes"),
        _p("cls2", "two-classes"),
        _p("cls1", "one-class"),
        _p("cls1", "three-classes"),
        _p("cls2", "three-classes"),
        _p("cls3", "three-classes"),
    ]
    result = finding_ids_shared_across_classes(problems)
    assert "two-classes" in result, "2 classes → included"
    assert "three-classes" in result, "3 classes → included"
    assert "one-class" not in result, "1 class → excluded"
