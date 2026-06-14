"""Item 255: top_classes_by_severity() — N classes with most problems at severity (2026-06-08).

``top_classes_by_severity(problems: list[Problem], severity: str, n: int)
-> list[str]``:
Returns at most *n* class names ranked by their problem count at *severity*
(descending).  Tie-break: class name ascending alphabetically.  Classes not
present at *severity* are excluded.  Empty or n=0 → ``[]``.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: ranking is by count AT the target severity, not by total
     problem count.  Kills impl ranking by class's total problem count.
  2. Tie-break is alphabetically ascending class name.
     Kills impl with unstable sort or wrong tie-break direction.
  3. n=0 → [].
     Kills impl that ignores n=0 and returns all ranked classes.
  4. Classes with no problems at the target severity are excluded.
     Kills impl that includes zero-count classes from other severities.
  5. Return type is list[str] (not frozenset or dict).
     Kills impl returning a set or {class: count} dict.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    top_classes_by_severity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_ranked_by_count_at_target_severity_not_total() -> None:
    """Ranking is by count at the target severity, not by total count.

    PRIMARY DISCRIMINATOR: kills impl that ranks by total problem count.
    alpha: 1 HIGH + 5 LOW (total=6), beta: 3 HIGH (total=3).
    Ranked by HIGH count: beta=3 > alpha=1 → beta first.
    If ranked by total: alpha(6) > beta(3) → wrong order.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "LOW"),
        _ps("alpha", 2, "LOW"),
        _ps("alpha", 3, "LOW"),
        _ps("alpha", 4, "LOW"),
        _ps("alpha", 5, "LOW"),
        _ps("beta", 0, "HIGH"),
        _ps("beta", 1, "HIGH"),
        _ps("beta", 2, "HIGH"),
    ]
    result = top_classes_by_severity(problems, "HIGH", 2)
    assert result == ["beta", "alpha"], "beta has 3 HIGH > alpha 1 HIGH → beta first; got " + repr(
        result
    )


def test_tie_break_is_alphabetically_ascending() -> None:
    """When counts are equal, class names are sorted alphabetically ascending.

    Kills impl with unstable sort or descending tie-break.
    gamma, alpha, mu all have 2 HIGH each → alpha < gamma < mu.
    """
    problems = [
        _ps("gamma", 0, "HIGH"),
        _ps("gamma", 1, "HIGH"),
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "HIGH"),
        _ps("mu", 0, "HIGH"),
        _ps("mu", 1, "HIGH"),
    ]
    result = top_classes_by_severity(problems, "HIGH", 3)
    assert result == ["alpha", "gamma", "mu"], "Tie-break alphabetically ascending; got " + repr(
        result
    )


def test_n_zero_returns_empty_list() -> None:
    """n=0 → [].

    Kills impl that ignores n and returns all ranked classes.
    """
    problems = [_ps("alpha", 0, "HIGH")]
    result = top_classes_by_severity(problems, "HIGH", 0)
    assert result == [], "n=0 → []; got " + repr(result)


def test_classes_not_at_target_severity_excluded() -> None:
    """Classes with no problems at the target severity are excluded from result.

    Kills impl that includes classes from other severities with count=0.
    beta has only LOW problems; asking for HIGH → beta excluded.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("beta", 0, "LOW"),
    ]
    result = top_classes_by_severity(problems, "HIGH", 5)
    assert "beta" not in result, "beta has no HIGH → must be excluded; got " + repr(result)
    assert "alpha" in result, "alpha has HIGH → must be included"


def test_return_type_is_list_of_str() -> None:
    """Return type is list[str].

    Kills impl returning frozenset or {class: count} dict.
    """
    problems = [_ps("alpha", 0, "CRITICAL"), _ps("beta", 0, "CRITICAL")]
    result = top_classes_by_severity(problems, "CRITICAL", 5)
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    for item in result:
        assert isinstance(item, str), "Elements must be str; got " + repr(type(item))
