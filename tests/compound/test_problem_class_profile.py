"""Item 296: problem_class_profile() — structured summary for a single class (2026-06-08).

``problem_class_profile(problems: list[Problem], cls: str) -> dict[str, object]``:
Returns {"total": int, "unique_ids": int, "labelling_coverage": float,
         "dominant_severity": str | None, "severity_counts": dict[str, int]}.
Absent class -> all-zero/None/empty profile.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: "unique_ids" is count of DISTINCT finding_ids, not total Problems.
     Kills impl using len(problems_in_class) as unique_ids.
  2. All keys present even for absent class (no missing keys, no None for dicts).
     Kills impl raising KeyError or returning None for absent class.
  3. "labelling_coverage" is cls-scoped (own total), not global.
     Kills impl dividing by global problem count.
  4. "dominant_severity" is None when all problems unlabelled.
     Kills impl returning "" or raising for unlabelled class.
  5. "severity_counts" excludes unlabelled (severity='') problems.
     Kills impl that includes unlabelled in severity_counts.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problem_class_profile,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_unique_ids_counts_distinct_finding_ids() -> None:
    """'unique_ids' is count of DISTINCT finding_ids, not total Problems.

    PRIMARY DISCRIMINATOR: kills impl using len(problems_in_class).
    alpha has 3 Problem records but only 2 distinct finding_ids.
    total=3 but unique_ids=2.
    """
    problems = [
        _ps("alpha", "id1", "HIGH"),
        _ps("alpha", "id1", "LOW"),  # same finding_id, different severity
        _ps("alpha", "id2", "HIGH"),
        _ps("beta", "id3", "CRITICAL"),
    ]
    profile = problem_class_profile(problems, "alpha")
    assert profile["total"] == 3, "3 Problem records in alpha; got " + repr(profile["total"])
    assert profile["unique_ids"] == 2, (
        "2 distinct finding_ids in alpha; got " + repr(profile["unique_ids"])
    )


def test_all_keys_present_for_absent_class() -> None:
    """All 5 keys present even when the class is absent.

    Kills impl raising KeyError or returning incomplete dict for missing class.
    """
    problems = [_ps("alpha", "id1", "HIGH")]
    profile = problem_class_profile(problems, "missing_class")
    required_keys = {"total", "unique_ids", "labelling_coverage", "dominant_severity", "severity_counts"}
    assert required_keys <= set(profile.keys()), (
        "All keys must be present; missing: "
        + repr(required_keys - set(profile.keys()))
    )
    assert profile["total"] == 0, "Absent class total=0; got " + repr(profile["total"])
    assert profile["unique_ids"] == 0, "Absent class unique_ids=0; got " + repr(profile["unique_ids"])
    assert profile["dominant_severity"] is None, (
        "Absent class dominant_severity=None; got " + repr(profile["dominant_severity"])
    )
    assert profile["severity_counts"] == {}, (
        "Absent class severity_counts={}; got " + repr(profile["severity_counts"])
    )


def test_labelling_coverage_is_class_scoped() -> None:
    """'labelling_coverage' uses cls's own total, not global total.

    Kills impl dividing cls_labelled_count by global_total.
    alpha: 1 labelled, 1 unlabelled -> 0.5 for alpha.
    beta: 1 labelled -> 1.0.
    Global: 2 labelled / 3 total = 0.667, NOT alpha's coverage.
    """
    problems = [
        _ps("alpha", "a1", "HIGH"),
        _p("alpha", "a2"),   # unlabelled
        _ps("beta", "b1", "LOW"),
    ]
    profile = problem_class_profile(problems, "alpha")
    assert abs(profile["labelling_coverage"] - 0.5) < 1e-9, (
        "alpha: 1/2 labelled = 0.5; got " + repr(profile["labelling_coverage"])
    )


def test_dominant_severity_is_none_for_unlabelled_class() -> None:
    """'dominant_severity' is None when all problems in cls are unlabelled.

    Kills impl returning '' or raising for unlabelled-only class.
    """
    problems = [_p("alpha", "id1"), _p("alpha", "id2")]
    profile = problem_class_profile(problems, "alpha")
    assert profile["dominant_severity"] is None, (
        "All unlabelled -> dominant_severity=None; got "
        + repr(profile["dominant_severity"])
    )


def test_severity_counts_excludes_unlabelled() -> None:
    """'severity_counts' only includes labelled severities (not severity='').

    Kills impl that includes '' key in severity_counts.
    alpha: 2 HIGH, 1 LOW, 1 unlabelled -> {'HIGH': 2, 'LOW': 1} with no '' key.
    """
    problems = [
        _ps("alpha", "id1", "HIGH"),
        _ps("alpha", "id2", "HIGH"),
        _ps("alpha", "id3", "LOW"),
        _p("alpha", "id4"),   # unlabelled
    ]
    profile = problem_class_profile(problems, "alpha")
    assert "" not in profile["severity_counts"], (
        "Unlabelled (severity='') excluded from severity_counts; got "
        + repr(profile["severity_counts"])
    )
    assert profile["severity_counts"] == {"HIGH": 2, "LOW": 1}, (
        "severity_counts={'HIGH': 2, 'LOW': 1}; got " + repr(profile["severity_counts"])
    )
