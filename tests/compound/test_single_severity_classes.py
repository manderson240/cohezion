"""Item 334: single_severity_classes() — classes with exactly one labelled severity (2026-06-08).

``single_severity_classes(problems) -> frozenset[str]``:
Complement of multi_severity_classes.  Returns frozenset of class names with
labelled problems at exactly 1 distinct severity value.
Unlabelled-only classes excluded.  Empty input -> frozenset().  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: class with all problems at ONE severity IS in result.
     Kills impl returning all classes or empty.
  2. Class with 2 distinct severities is NOT in result.
     Kills impl treating count-of-records as count-of-severities.
  3. multi_severity_classes + single_severity_classes partition all labelled classes.
     Kills impl with overlap or missing classes.
  4. Empty input returns frozenset().
     Kills impl raising on empty.
  5. Unlabelled-only class is NOT in result.
     Kills impl treating unlabelled as a severity.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    multi_severity_classes,
    single_severity_classes,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_class_with_one_severity_is_included() -> None:
    """Class whose all labelled problems share a single severity is in result.

    PRIMARY DISCRIMINATOR: kills impl returning all classes or empty.
    alpha: 3 HIGH records (all same severity) -> in single_severity_classes.
    beta: HIGH + LOW -> NOT in single.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "HIGH"),
        _ps("alpha", 2, "HIGH"),
        _ps("beta", 0, "HIGH"),
        _ps("beta", 1, "LOW"),
    ]
    result = single_severity_classes(problems)
    assert "alpha" in result, "alpha has only HIGH -> in single_severity_classes"
    assert "beta" not in result, "beta has HIGH+LOW -> NOT in single"


def test_class_with_two_severities_excluded() -> None:
    """Class with 2 distinct severities is NOT in result.

    Kills impl counting records instead of distinct severities.
    """
    problems = [_ps("alpha", 0, "HIGH"), _ps("alpha", 1, "LOW")]
    result = single_severity_classes(problems)
    assert "alpha" not in result, (
        "alpha has HIGH+LOW (2 severities) -> NOT in single; got " + repr(result)
    )


def test_multi_and_single_partition_labelled_classes() -> None:
    """multi_severity_classes ∪ single_severity_classes == all classes with >=1 labelled problem.

    Kills impl with overlap or gap in the partition.
    alpha: 2 severities -> multi. beta: 1 severity -> single.
    gamma: unlabelled only -> neither.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "LOW"),
        _ps("beta", 0, "HIGH"),
        _p("gamma", 0),  # unlabelled
    ]
    multi = multi_severity_classes(problems)
    single = single_severity_classes(problems)
    assert multi & single == frozenset(), "multi ∩ single must be empty (disjoint)"
    labelled_classes = {p.problem_class for p in problems if p.severity}
    assert multi | single == labelled_classes, (
        "multi ∪ single must equal all labelled classes; got "
        + repr(multi | single) + " vs " + repr(labelled_classes)
    )


def test_empty_input_returns_empty_frozenset() -> None:
    """Empty input returns frozenset() without raising."""
    result = single_severity_classes([])
    assert result == frozenset(), "empty -> frozenset(); got " + repr(result)


def test_unlabelled_only_class_excluded() -> None:
    """Class with only unlabelled problems is NOT in result.

    Kills impl treating unlabelled (severity='') as a valid severity.
    """
    problems = [_p("alpha", 0), _p("alpha", 1)]
    result = single_severity_classes(problems)
    assert "alpha" not in result, (
        "alpha has only unlabelled -> not in single_severity_classes; got " + repr(result)
    )
