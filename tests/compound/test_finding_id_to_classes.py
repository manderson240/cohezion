"""Item 375: finding_id_to_classes() -- reverse index: fid -> frozenset of classes (2026-06-08).

``finding_id_to_classes(problems) -> dict[str, frozenset[str]]``:
Returns a dict mapping each distinct finding_id to the frozenset of
problem_class names that have at least one Problem with that finding_id.
Empty -> {}.  Single-class fids map to frozenset of size 1.  Pure; no I/O.

Discriminating tests:

  1. PRIMARY DISC.: maps finding_id -> SET of classes (not class -> fids).
     Kills impl returning the reverse mapping.
  2. Values are frozensets of class name strings (not Problem objects).
     Kills impl mapping fid -> list[Problem].
  3. Single-class finding_id maps to frozenset of size 1.
     Kills impl excluding single-class fids.
  4. Empty input returns {} without raising.
     Kills impl raising on empty.
  5. Multi-class finding_id maps to frozenset of all owning classes.
     Kills impl keeping only first class seen.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    finding_id_to_classes,
)


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_maps_fid_to_classes_not_reverse() -> None:
    """Keys are finding_ids, values are class sets — not the reverse.

    PRIMARY DISCRIMINATOR: kills impl returning class -> frozenset(fids).
    """
    problems = [_p("sec", "CVE-001"), _p("perf", "CVE-001"), _p("sec", "CVE-002")]
    result = finding_id_to_classes(problems)
    assert "CVE-001" in result, "CVE-001 must be a key"
    assert isinstance(result["CVE-001"], frozenset), "Value must be frozenset"
    assert result["CVE-001"] == frozenset({"sec", "perf"}), (
        "CVE-001 is in sec and perf; got " + repr(result["CVE-001"])
    )


def test_values_are_frozensets_of_strings() -> None:
    """Values are frozensets of class name strings, not Problem objects.

    Kills impl mapping fid -> list[Problem].
    """
    problems = [_p("alpha", "f:0"), _p("beta", "f:0")]
    result = finding_id_to_classes(problems)
    value = result["f:0"]
    assert isinstance(value, frozenset), "Value must be frozenset"
    assert all(isinstance(v, str) for v in value), "Elements must be strings"


def test_single_class_fid_maps_to_size_one_frozenset() -> None:
    """Single-class finding_id maps to frozenset of size 1.

    Kills impl excluding single-class fids or requiring multi-class overlap.
    """
    problems = [_p("sec", "CVE-001"), _p("sec", "CVE-002")]
    result = finding_id_to_classes(problems)
    assert result["CVE-001"] == frozenset({"sec"}), "CVE-001 in only sec; got " + repr(
        result.get("CVE-001")
    )
    assert result["CVE-002"] == frozenset({"sec"})


def test_empty_returns_empty_dict() -> None:
    """Empty input returns {} without raising."""
    assert finding_id_to_classes([]) == {}


def test_multi_class_fid_maps_to_all_classes() -> None:
    """Multi-class finding_id maps to all owning classes.

    Kills impl keeping only first class seen.
    """
    problems = [
        _p("sec", "shared"),
        _p("perf", "shared"),
        _p("style", "shared"),
        _p("sec", "unique"),
    ]
    result = finding_id_to_classes(problems)
    assert result["shared"] == frozenset({"sec", "perf", "style"}), (
        "shared in 3 classes; got " + repr(result.get("shared"))
    )
    assert result["unique"] == frozenset({"sec"})
