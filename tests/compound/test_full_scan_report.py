"""Item 297: full_scan_report() — richer top-level scan summary dict (2026-06-08).

Note: the backlog originally named this scan_summary() but that name is already
taken by item 268 (with different keys).  This function uses the name
full_scan_report() to avoid the conflict per the non-destructive wiring policy.

``full_scan_report(problems: list[Problem]) -> dict[str, object]``:
Returns {"total": int, "unique_ids": int, "class_count": int,
         "labelling_coverage": float, "severity_distribution": dict[str, int],
         "top_class_by_count": str | None, "most_critical_class": str | None}.
Empty -> all-zero/None/empty.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: "unique_ids" is globally distinct finding_ids count,
     not sum of per-class unique_ids (which double-counts shared ids).
     Kills impl summing per_class unique_ids.
  2. "most_critical_class" = class with most CRITICAL problems; fallback
     to class with most HIGH if no CRITICAL.
     Kills impl ignoring CRITICAL or not falling back to HIGH.
  3. Empty input -> all-zero/None/empty, all 7 keys present.
     Kills impl raising or omitting keys on empty.
  4. "severity_distribution" excludes unlabelled (severity='') problems.
     Kills impl including '' key.
  5. All 7 required keys present in result.
     Kills impl returning fewer keys.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    full_scan_report,
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


def test_unique_ids_is_globally_distinct() -> None:
    """'unique_ids' counts globally distinct finding_ids, not sum of per-class counts.

    PRIMARY DISCRIMINATOR: kills impl summing per-class unique_ids.
    'shared' appears in alpha and beta -> counts as 1 globally, not 2.
    """
    problems = [
        _ps("alpha", "shared", "HIGH"),
        _ps("beta", "shared", "LOW"),
        _ps("alpha", "only_alpha", "HIGH"),
    ]
    report = full_scan_report(problems)
    assert report["unique_ids"] == 2, (
        "'shared' + 'only_alpha' = 2 globally distinct ids; "
        "per-class sum would give 3; got " + repr(report["unique_ids"])
    )


def test_most_critical_class_falls_back_to_high() -> None:
    """'most_critical_class' falls back to class with most HIGH when no CRITICAL.

    Kills impl that returns None or wrong class when CRITICAL is absent.
    alpha: 3 HIGH problems. beta: 1 HIGH problem.
    No CRITICAL -> fallback to HIGH -> alpha wins (3 vs 1).
    """
    problems = [
        _ps("alpha", "a1", "HIGH"),
        _ps("alpha", "a2", "HIGH"),
        _ps("alpha", "a3", "HIGH"),
        _ps("beta", "b1", "HIGH"),
    ]
    report = full_scan_report(problems)
    assert report["most_critical_class"] == "alpha", (
        "alpha has most HIGH (no CRITICAL) -> most_critical_class='alpha'; got "
        + repr(report["most_critical_class"])
    )


def test_empty_input_returns_all_keys_with_zero_values() -> None:
    """Empty input returns a dict with all 7 keys, all zero/None/empty.

    Kills impl raising or omitting keys on empty.
    """
    report = full_scan_report([])
    required_keys = {
        "total",
        "unique_ids",
        "class_count",
        "labelling_coverage",
        "severity_distribution",
        "top_class_by_count",
        "most_critical_class",
    }
    assert required_keys <= set(report.keys()), "All 7 keys must be present; missing: " + repr(
        required_keys - set(report.keys())
    )
    assert report["total"] == 0, "Empty -> total=0; got " + repr(report["total"])
    assert report["most_critical_class"] is None, "Empty -> most_critical_class=None; got " + repr(
        report["most_critical_class"]
    )


def test_severity_distribution_excludes_unlabelled() -> None:
    """'severity_distribution' excludes unlabelled (severity='') problems.

    Kills impl that includes '' key in the distribution.
    """
    problems = [
        _ps("alpha", "id1", "HIGH"),
        _p("alpha", "id2"),  # unlabelled
    ]
    report = full_scan_report(problems)
    assert "" not in report["severity_distribution"], (
        "Unlabelled excluded from severity_distribution; got "
        + repr(report["severity_distribution"])
    )
    assert report["severity_distribution"] == {"HIGH": 1}, "Only 1 HIGH; got " + repr(
        report["severity_distribution"]
    )


def test_all_seven_keys_present() -> None:
    """All 7 required keys present in result.

    Kills impl returning fewer keys.
    """
    problems = [_ps("alpha", "id1", "CRITICAL")]
    report = full_scan_report(problems)
    required_keys = {
        "total",
        "unique_ids",
        "class_count",
        "labelling_coverage",
        "severity_distribution",
        "top_class_by_count",
        "most_critical_class",
    }
    assert required_keys <= set(report.keys()), (
        "Required keys: " + repr(required_keys) + "; got: " + repr(set(report.keys()))
    )
