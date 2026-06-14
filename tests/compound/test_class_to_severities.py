"""Item 378: class_to_severities() -- class -> frozenset of distinct severities (2026-06-08).

``class_to_severities(problems) -> dict[str, frozenset[str]]``:
Returns a dict mapping each distinct problem_class to the frozenset of distinct
severity strings present among its problems.  Unlabelled '' is included as a
severity if any unlabelled Problem is present.  Empty -> {}.  Pure; no I/O.

Discriminating tests:

  1. PRIMARY DISC.: maps class -> SET of severities (not class -> finding_ids or Problems).
     Kills impl delegating to class_to_finding_ids.
  2. Unlabelled '' is included as a severity when present.
     Kills impl filtering out unlabelled.
  3. Each class appears exactly once as key.
     Kills impl creating duplicate keys.
  4. Empty input returns {}.
     Kills impl raising on empty.
  5. Multiple problems with same class+severity -> severity appears once in frozenset.
     Kills impl counting occurrences.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_to_severities,
)


def _p(cls: str, fid: str, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_maps_class_to_severities_not_fids() -> None:
    """Values are frozensets of severity strings, not finding_ids.

    PRIMARY DISCRIMINATOR: kills impl delegating to class_to_finding_ids.
    """
    problems = [_p("sec", "CVE-001", "HIGH"), _p("sec", "CVE-002", "LOW")]
    result = class_to_severities(problems)
    assert "sec" in result, "sec must be a key"
    value = result["sec"]
    assert isinstance(value, frozenset), "Value must be frozenset"
    assert all(isinstance(v, str) for v in value), "Elements must be strings"
    assert value == frozenset({"HIGH", "LOW"}), "sec has HIGH and LOW; got " + repr(value)


def test_unlabelled_included_as_empty_string_severity() -> None:
    """'' severity is included when any unlabelled problem is in the class.

    Kills impl filtering out unlabelled problems before building the index.
    """
    problems = [_p("sec", "CVE-001", "HIGH"), _p("sec", "CVE-002")]  # CVE-002 unlabelled
    result = class_to_severities(problems)
    assert "" in result["sec"], "'' must be in sec's severity set; got " + repr(result.get("sec"))
    assert "HIGH" in result["sec"]


def test_each_class_appears_once_as_key() -> None:
    """Each distinct class appears exactly once as key."""
    problems = [
        _p("a", "f:0", "HIGH"),
        _p("a", "f:1", "LOW"),
        _p("b", "f:2", "MEDIUM"),
    ]
    result = class_to_severities(problems)
    assert set(result.keys()) == {"a", "b"}, "Keys must be a, b; got " + repr(set(result.keys()))


def test_empty_returns_empty_dict() -> None:
    """Empty input returns {} without raising."""
    assert class_to_severities([]) == {}


def test_repeated_severity_appears_once() -> None:
    """Same class+severity across multiple problems -> severity appears once in frozenset.

    Kills impl counting occurrences instead of using a set.
    """
    problems = [_p("sec", f"f:{i}", "HIGH") for i in range(5)]
    result = class_to_severities(problems)
    assert result["sec"] == frozenset({"HIGH"}), "HIGH×5 under sec -> appears once; got " + repr(
        result.get("sec")
    )
