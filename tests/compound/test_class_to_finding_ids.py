"""Item 376: class_to_finding_ids() -- forward index: class -> frozenset of fids (2026-06-08).

``class_to_finding_ids(problems) -> dict[str, frozenset[str]]``:
Returns a dict mapping each distinct problem_class to the frozenset of
finding_ids that appear under it.  Mirror of finding_id_to_classes
with keys/values swapped.  Empty -> {}.  Pure; no I/O.

Discriminating tests:

  1. PRIMARY DISC.: maps class -> SET of finding_ids (not the reverse).
     Kills impl returning finding_id_to_classes.
  2. Values are frozensets of finding_id strings, not Problem objects.
     Kills impl mapping class -> list[Problem].
  3. Multiple records with same class/fid deduplicated in value frozenset.
     Kills impl counting duplicates.
  4. Empty input returns {}.
     Kills impl raising on empty.
  5. Each class appears exactly once as key.
     Kills impl creating duplicate keys or missing classes.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_to_finding_ids,
)


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_maps_class_to_finding_ids_not_reverse() -> None:
    """Keys are class names, values are frozensets of finding_ids.

    PRIMARY DISCRIMINATOR: kills impl returning finding_id_to_classes.
    """
    problems = [_p("sec", "CVE-001"), _p("sec", "CVE-002"), _p("perf", "CVE-001")]
    result = class_to_finding_ids(problems)
    assert "sec" in result, "sec must be a key"
    assert isinstance(result["sec"], frozenset), "Value must be frozenset"
    assert result["sec"] == frozenset({"CVE-001", "CVE-002"}), (
        "sec has CVE-001 and CVE-002; got " + repr(result["sec"])
    )
    assert result["perf"] == frozenset({"CVE-001"}), "perf has CVE-001 only; got " + repr(
        result.get("perf")
    )


def test_values_are_frozensets_of_fid_strings() -> None:
    """Values are frozensets of finding_id strings, not Problem objects.

    Kills impl mapping class -> list[Problem].
    """
    problems = [_p("alpha", "f:0"), _p("alpha", "f:1")]
    result = class_to_finding_ids(problems)
    value = result["alpha"]
    assert isinstance(value, frozenset), "Value must be frozenset"
    assert all(isinstance(v, str) for v in value), "Elements must be strings"


def test_duplicate_fids_deduplicated_in_value() -> None:
    """Same class+fid in multiple records → fid appears once in value frozenset.

    Kills impl counting duplicates instead of using a set.
    """
    problems = [_p("sec", "CVE-001"), _p("sec", "CVE-001"), _p("sec", "CVE-001")]
    result = class_to_finding_ids(problems)
    assert result["sec"] == frozenset({"CVE-001"}), "Same fid thrice -> appears once; got " + repr(
        result.get("sec")
    )


def test_empty_returns_empty_dict() -> None:
    """Empty input returns {} without raising."""
    assert class_to_finding_ids([]) == {}


def test_each_class_appears_once_as_key() -> None:
    """Each distinct class appears exactly once as a key.

    Kills impl that creates duplicate keys or misses classes.
    """
    problems = [
        _p("a", "f:0"),
        _p("a", "f:1"),
        _p("b", "f:2"),
        _p("c", "f:3"),
        _p("c", "f:4"),
        _p("c", "f:5"),
    ]
    result = class_to_finding_ids(problems)
    assert set(result.keys()) == {"a", "b", "c"}, "All 3 classes as keys; got " + repr(
        set(result.keys())
    )
    assert len(result["a"]) == 2
    assert len(result["b"]) == 1
    assert len(result["c"]) == 3
