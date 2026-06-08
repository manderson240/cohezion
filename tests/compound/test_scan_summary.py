"""Item 268: scan_summary() — one-call full-scan summary dict (2026-06-08).

``scan_summary(problems: list[Problem]) -> dict[str, object]``:
Returns a dict with exactly seven keys summarising a scan::

    {
        "total":            int,         # len(problems)
        "labelled":         int,         # labelled_problem_count
        "coverage":         float,       # labelling_coverage
        "class_count":      int,         # distinct problem_class count
        "severity_counts":  dict,        # count_by_severity (excludes "")
        "dominant_severity": str | None, # dominant_severity
        "has_duplicates":   bool,        # bool(duplicate_finding_ids)
    }

Empty input → all zeros/None/False/{}.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: exactly seven keys present.
     Kills impl missing any key or adding extra keys.
  2. "has_duplicates" is False when all finding_ids are unique.
     Kills impl always returning True.
  3. "coverage" uses total denominator (labelled/total), not 1.0 always.
     Kills impl computing labelled/labelled.
  4. Empty input → all zeros/None/False/{}.
     Kills impl raising on empty.
  5. "class_count" counts distinct classes, not total problems.
     Kills impl returning len(problems) for class_count.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    scan_summary,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


def _unlab(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


_EXPECTED_KEYS = {
    "total", "labelled", "coverage", "class_count",
    "severity_counts", "dominant_severity", "has_duplicates",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_exactly_seven_keys() -> None:
    """Return dict has exactly the seven specified keys.

    PRIMARY DISCRIMINATOR: kills impl missing any key or adding extras.
    """
    result = scan_summary([_ps("alpha", 0, "HIGH")])
    assert set(result.keys()) == _EXPECTED_KEYS, (
        "Must have exactly 7 keys; got " + repr(set(result.keys()))
    )


def test_has_duplicates_false_when_all_unique() -> None:
    """has_duplicates is False when all finding_ids are unique.

    Kills impl always returning True for has_duplicates.
    """
    problems = [_ps("alpha", i, "HIGH") for i in range(5)]
    result = scan_summary(problems)
    assert result["has_duplicates"] is False, (
        "All unique ids → has_duplicates=False; got " + repr(result["has_duplicates"])
    )
    # Also verify True case
    p = Problem(problem_class="beta", finding_id="beta:dup")
    result2 = scan_summary([p, p])
    assert result2["has_duplicates"] is True, "Duplicate id → has_duplicates=True"


def test_coverage_uses_total_denominator() -> None:
    """coverage = labelled / total (not labelled/labelled=1.0).

    Kills impl computing labelled/labelled.
    3 labelled + 3 unlabelled → coverage = 0.5.
    """
    problems = [
        _ps("a", 0, "HIGH"), _ps("a", 1, "LOW"), _ps("a", 2, "CRITICAL"),
        _unlab("b", 0), _unlab("b", 1), _unlab("b", 2),
    ]
    result = scan_summary(problems)
    assert abs(result["coverage"] - 0.5) < 1e-9, (
        "3/6 → coverage=0.5; got " + repr(result["coverage"])
    )


def test_empty_input_returns_zero_state() -> None:
    """Empty input → all zeros/None/False/{}.

    Kills impl raising on empty.
    """
    result = scan_summary([])
    assert result["total"] == 0
    assert result["labelled"] == 0
    assert result["coverage"] == 0.0
    assert result["class_count"] == 0
    assert result["severity_counts"] == {}
    assert result["dominant_severity"] is None
    assert result["has_duplicates"] is False


def test_class_count_is_distinct_classes_not_total() -> None:
    """class_count = distinct class names, not total problems.

    Kills impl returning len(problems) for class_count.
    alpha appears 5× but counts as 1 class; plus beta = 2 classes.
    """
    problems = [_ps("alpha", i, "HIGH") for i in range(5)] + [_ps("beta", 0, "LOW")]
    result = scan_summary(problems)
    assert result["class_count"] == 2, (
        "alpha + beta = 2 distinct classes (not 6 problems); got "
        + repr(result["class_count"])
    )
