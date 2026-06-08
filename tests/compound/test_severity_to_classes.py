"""Item 379: severity_to_classes() -- severity -> frozenset of class names (2026-06-08).

``severity_to_classes(problems) -> dict[str, frozenset[str]]``:
Returns a dict mapping each distinct severity string to the frozenset of
problem_class names that have at least one Problem with that severity.
Unlabelled '' is included as a key when any unlabelled Problem is present.
Empty -> {}.  Pure; no I/O.  Transpose of class_to_severities.

Discriminating tests:

  1. PRIMARY DISC.: maps severity -> SET of CLASS NAMES (not finding_ids).
     Kills impl delegating to severity_to_finding_ids.
  2. Unlabelled '' is a key when any unlabelled problem is present.
     Kills impl filtering out unlabelled problems.
  3. Duplicate class names under same severity collapsed to one entry in frozenset.
     Kills impl counting occurrences instead of using a set.
  4. Empty input returns {}.
     Kills impl raising on empty.
  5. Each severity appears exactly once as key.
     Kills impl creating duplicate keys or missing severities.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_to_classes,
)


def _p(cls: str, fid: str, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_maps_severity_to_classes_not_fids() -> None:
    """Values are frozensets of class name strings, not finding_ids.

    PRIMARY DISCRIMINATOR: kills impl delegating to severity_to_finding_ids.
    """
    problems = [_p("sec", "CVE-001", "HIGH"), _p("perf", "PERF-001", "HIGH")]
    result = severity_to_classes(problems)
    assert "HIGH" in result, "HIGH must be a key"
    value = result["HIGH"]
    assert isinstance(value, frozenset), "Value must be frozenset"
    assert all(isinstance(v, str) for v in value), "Elements must be strings"
    assert value == frozenset({"sec", "perf"}), "HIGH has sec and perf; got " + repr(value)


def test_unlabelled_included_as_key() -> None:
    """'' is included as a key when any unlabelled problem is present.

    Kills impl filtering out unlabelled problems before building the index.
    """
    problems = [_p("sec", "CVE-001", "HIGH"), _p("style", "STY-001")]  # STY-001 unlabelled
    result = severity_to_classes(problems)
    assert "" in result, "'' must be a key; got " + repr(set(result.keys()))
    assert result[""] == frozenset({"style"}), "'' maps to style; got " + repr(result.get(""))


def test_duplicate_classes_collapsed_in_value() -> None:
    """Multiple problems with same severity+class -> class appears once in frozenset.

    Kills impl counting occurrences instead of using a set.
    """
    problems = [_p("sec", f"f:{i}", "HIGH") for i in range(4)]
    result = severity_to_classes(problems)
    assert result["HIGH"] == frozenset({"sec"}), (
        "sec×4 under HIGH -> sec appears once; got " + repr(result.get("HIGH"))
    )


def test_empty_returns_empty_dict() -> None:
    """Empty input returns {} without raising."""
    assert severity_to_classes([]) == {}


def test_each_severity_appears_once_as_key() -> None:
    """Each distinct severity appears exactly once as a key.

    Kills impl that creates duplicate keys or misses severities.
    """
    problems = [
        _p("a", "f:0", "HIGH"),
        _p("b", "f:1", "LOW"),
        _p("c", "f:2"),  # unlabelled
    ]
    result = severity_to_classes(problems)
    assert set(result.keys()) == {"HIGH", "LOW", ""}, "Keys must be HIGH, LOW, ''; got " + repr(
        set(result.keys())
    )
    assert len(result["HIGH"]) == 1
    assert len(result["LOW"]) == 1
    assert len(result[""]) == 1
