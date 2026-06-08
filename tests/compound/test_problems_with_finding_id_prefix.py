"""Item 359: problems_with_finding_id_prefix() -- filter by finding_id prefix (2026-06-08).

``problems_with_finding_id_prefix(problems, prefix) -> list[Problem]``:
Returns all Problem objects whose finding_id.startswith(prefix).
Mirror of problems_with_class_prefix on the finding_id axis.
Empty prefix matches all.  Case-sensitive.  Preserves order.
Empty -> [].  Pure; no I/O.

Discriminating tests:

  1. PRIMARY DISC.: filters on finding_id not problem_class.
     Kills impl re-using class_prefix logic on wrong field.
  2. Empty prefix matches ALL problems.
     Kills impl returning [] for empty prefix.
  3. Non-matching prefix returns [].
     Kills impl returning all problems on unknown prefix.
  4. Case-sensitive (prefix 'CVE-' does not match 'cve-').
     Kills case-insensitive impl.
  5. Original insertion order preserved.
     Kills impl that reorders.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_with_finding_id_prefix,
)


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_filters_on_finding_id_not_class() -> None:
    """Filters by finding_id.startswith(prefix), not class name.

    PRIMARY DISCRIMINATOR: kills impl filtering on problem_class.
    Same class 'sec', different finding_ids; prefix='CVE-' matches only CVE fids.
    """
    problems = [_p("sec", "CVE-2024-001"), _p("sec", "CVE-2024-002"), _p("sec", "JIRA-001")]
    result = problems_with_finding_id_prefix(problems, "CVE-")
    assert len(result) == 2, "2 CVE findings; got " + repr(len(result))
    assert all(p.finding_id.startswith("CVE-") for p in result)
    assert all(isinstance(p, Problem) for p in result)


def test_empty_prefix_matches_all() -> None:
    """Empty prefix returns ALL problems.

    Kills impl returning [] for empty prefix.
    """
    problems = [_p("a", "CVE-001"), _p("b", "JIRA-001"), _p("c", "SEC-001")]
    result = problems_with_finding_id_prefix(problems, "")
    assert len(result) == 3, "Empty prefix -> all; got " + repr(len(result))


def test_non_matching_prefix_returns_empty() -> None:
    """Unknown prefix returns []."""
    problems = [_p("a", "CVE-001"), _p("b", "JIRA-001")]
    assert problems_with_finding_id_prefix(problems, "ZZZ-") == []


def test_case_sensitive() -> None:
    """Matching is case-sensitive.

    Kills case-insensitive impl.
    """
    problems = [_p("a", "CVE-001"), _p("b", "cve-001")]
    result = problems_with_finding_id_prefix(problems, "CVE-")
    assert len(result) == 1, "Only uppercase CVE-; got " + repr(result)
    assert result[0].finding_id == "CVE-001"


def test_original_order_preserved() -> None:
    """Insertion order preserved in result."""
    fids = ["CVE-003", "CVE-001", "CVE-002"]
    problems = [_p("x", fid) for fid in fids] + [_p("y", "JIRA-001")]
    result = problems_with_finding_id_prefix(problems, "CVE-")
    assert [p.finding_id for p in result] == fids, "Order preserved; got " + repr(
        [p.finding_id for p in result]
    )
