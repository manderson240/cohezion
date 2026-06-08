"""Item 377: severity_to_finding_ids() -- severity -> frozenset of fids (2026-06-08).

``severity_to_finding_ids(problems) -> dict[str, frozenset[str]]``:
Returns a dict mapping each distinct severity string to the frozenset of
finding_ids whose Problem records carry that severity.
Unlabelled '' is a key if any unlabelled problem is present.
Empty -> {}.  Pure; no I/O.

Discriminating tests:

  1. PRIMARY DISC.: maps severity -> SET of finding_ids (not severity -> list of Problems).
     Kills impl mapping severity -> list[Problem] or severity -> [problem_class].
  2. Unlabelled '' is a key when any unlabelled problem present.
     Kills impl that drops '' severity.
  3. Duplicate finding_ids under same severity deduplicated.
     Kills impl counting duplicates.
  4. Empty input returns {}.
     Kills impl raising on empty.
  5. Each severity appears exactly once as key.
     Kills impl creating duplicate keys.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_to_finding_ids,
)


def _p(cls: str, fid: str, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_maps_severity_to_finding_ids_not_problems() -> None:
    """Values are frozensets of finding_id strings, not Problem objects.

    PRIMARY DISCRIMINATOR: kills impl returning severity -> list[Problem].
    """
    problems = [_p("sec", "CVE-001", "HIGH"), _p("sec", "CVE-002", "HIGH")]
    result = severity_to_finding_ids(problems)
    assert "HIGH" in result, "HIGH must be a key"
    value = result["HIGH"]
    assert isinstance(value, frozenset), "Value must be frozenset"
    assert all(isinstance(v, str) for v in value), "Elements must be strings"
    assert value == frozenset({"CVE-001", "CVE-002"}), "HIGH has CVE-001, CVE-002; got " + repr(
        value
    )


def test_unlabelled_included_under_empty_key() -> None:
    """'' severity is a key when any unlabelled problem present.

    Kills impl that drops unlabelled problems.
    """
    problems = [_p("a", "f:0", "HIGH"), _p("b", "f:1")]  # f:1 has sev=''
    result = severity_to_finding_ids(problems)
    assert "" in result, "'' key must be present for unlabelled; got keys=" + repr(
        set(result.keys())
    )
    assert "f:1" in result[""], "f:1 is unlabelled; got " + repr(result.get(""))


def test_duplicate_fids_deduplicated() -> None:
    """Same finding_id under same severity in multiple records -> appears once.

    Kills impl counting duplicates.
    """
    problems = [_p("a", "CVE-001", "HIGH"), _p("b", "CVE-001", "HIGH")]
    result = severity_to_finding_ids(problems)
    assert result["HIGH"] == frozenset({"CVE-001"}), (
        "CVE-001 twice under HIGH -> appears once; got " + repr(result.get("HIGH"))
    )


def test_empty_returns_empty_dict() -> None:
    """Empty input returns {} without raising."""
    assert severity_to_finding_ids([]) == {}


def test_each_severity_appears_once_as_key() -> None:
    """Each distinct severity appears exactly once as a key."""
    problems = [
        _p("a", "f:0", "HIGH"),
        _p("b", "f:1", "HIGH"),
        _p("c", "f:2", "LOW"),
        _p("d", "f:3"),
    ]
    result = severity_to_finding_ids(problems)
    assert set(result.keys()) == {"HIGH", "LOW", ""}, "Keys must be HIGH, LOW, ''; got " + repr(
        set(result.keys())
    )
    assert len(result["HIGH"]) == 2
    assert len(result["LOW"]) == 1
    assert len(result[""]) == 1
