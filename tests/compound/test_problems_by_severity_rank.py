"""Item 347: problems_by_severity_rank() — sort problems by caller-supplied severity order (2026-06-08).

``problems_by_severity_rank(problems, severity_order) -> list[Problem]``:
Returns all Problem objects ordered by position of severity in severity_order
(lowest index = first); unlabelled/unknown severities appended last.
Ties within a tier preserve original insertion order (stable).
Empty input -> [].  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: CRITICAL before HIGH before MEDIUM (kills alphabetical sort).
     Kills impl that sorts alphabetically or by insertion order only.
  2. Unlabelled problems appended AFTER all ranked (not dropped).
     Kills impl dropping unlabelled or sorting them first.
  3. Ties within a severity tier preserve original insertion order (stable sort).
     Kills unstable sort.
  4. Empty input returns [].
     Kills impl raising on empty.
  5. Unknown severities (not in severity_order) treated same as unlabelled: appended last.
     Kills impl crashing on unknown severity.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_by_severity_rank,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_critical_before_high_before_medium() -> None:
    """CRITICAL < HIGH < MEDIUM in caller-supplied order.

    PRIMARY DISCRIMINATOR: kills alphabetical sort (CRITICAL > HIGH alphabetically).
    """
    problems = [
        _ps("a", 0, "MEDIUM"),
        _ps("b", 0, "CRITICAL"),
        _ps("c", 0, "HIGH"),
    ]
    result = problems_by_severity_rank(problems, ORDER)
    assert [p.severity for p in result] == ["CRITICAL", "HIGH", "MEDIUM"], (
        "Must follow ORDER rank; got " + repr([p.severity for p in result])
    )


def test_unlabelled_appended_after_ranked() -> None:
    """Unlabelled problems come after all ranked problems (not dropped).

    Kills impl dropping unlabelled or inserting them first.
    """
    problems = [_p("x", 0), _ps("y", 0, "HIGH"), _p("z", 0)]
    result = problems_by_severity_rank(problems, ORDER)
    assert len(result) == 3, "All problems returned; got " + repr(len(result))
    assert result[0].finding_id == "y:0", "Ranked first; got " + repr(result[0])
    assert {p.finding_id for p in result[1:]} == {"x:0", "z:0"}, (
        "Unlabelled last; got " + repr([p.finding_id for p in result])
    )


def test_ties_within_tier_preserve_insertion_order() -> None:
    """Multiple problems at same severity preserve original insertion order.

    Kills unstable sort implementation.
    """
    problems = [
        _ps("a", 0, "HIGH"),
        _ps("b", 0, "CRITICAL"),
        _ps("c", 0, "HIGH"),
        _ps("d", 0, "HIGH"),
    ]
    result = problems_by_severity_rank(problems, ORDER)
    high_ids = [p.finding_id for p in result if p.severity == "HIGH"]
    assert high_ids == ["a:0", "c:0", "d:0"], (
        "HIGH tier preserves insertion order; got " + repr(high_ids)
    )


def test_empty_input_returns_empty_list() -> None:
    """Empty input returns [] without raising."""
    assert problems_by_severity_rank([], ORDER) == []


def test_unknown_severity_appended_last() -> None:
    """Severity not in severity_order is treated same as unlabelled: appended last.

    Kills impl crashing on unknown severity.
    """
    problems = [
        _ps("a", 0, "UNKNOWN_SEV"),
        _ps("b", 0, "HIGH"),
        _ps("c", 0, "CRITICAL"),
    ]
    result = problems_by_severity_rank(problems, ORDER)
    assert result[0].severity == "CRITICAL", "CRITICAL first; got " + repr(result[0])
    assert result[1].severity == "HIGH", "HIGH second; got " + repr(result[1])
    assert result[2].finding_id == "a:0", "Unknown last; got " + repr(result[2])
