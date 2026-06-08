"""Item 257: severity_concentration_report() — per-class severity breakdown (2026-06-08).

``severity_concentration_report(problems, severity, min_fraction)
-> dict[str, dict[str, object]]``:
Returns a nested dict for every class with ≥1 problem::

    {
        class_name: {
            "total":             int,    # total problems in this class
            "at_severity":       int,    # problems at the target severity
            "fraction":          float,  # at_severity / total (per-class)
            "exceeds_threshold": bool,   # fraction >= min_fraction
        }
    }

Classes with 0 problems at the target severity still appear (at_severity=0).
Empty input → {}.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: each class entry has exactly the four keys.
     Kills impl returning a flat dict or omitting any key.
  2. "fraction" is per-class (at_severity/total), not global.
     Kills impl using severity_fraction(all_problems, severity).
  3. "exceeds_threshold" uses >= (inclusive) boundary.
     Kills impl using strictly >.
  4. Classes with 0 at_severity are still included (at_severity=0).
     Kills impl that skips classes with no problems at the target severity.
  5. Empty input → {}.
     Kills impl that raises on empty input.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_concentration_report,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_each_class_entry_has_four_keys() -> None:
    """Each class maps to a dict with exactly four keys.

    PRIMARY DISCRIMINATOR: kills impl returning a flat dict (class→count)
    or omitting any of the four required keys.
    """
    problems = [_ps("alpha", 0, "HIGH"), _ps("alpha", 1, "LOW")]
    result = severity_concentration_report(problems, "HIGH", 0.5)
    assert "alpha" in result, "alpha must appear in result"
    entry = result["alpha"]
    assert set(entry.keys()) == {"total", "at_severity", "fraction", "exceeds_threshold"}, (
        "Must have exactly four keys; got " + repr(set(entry.keys()))
    )


def test_fraction_is_per_class_not_global() -> None:
    """fraction is computed per-class (at_severity/total), not globally.

    Kills impl using global severity_fraction(all, severity).
    alpha: 1 HIGH / 2 total = 0.5.  beta: 5 LOW (no HIGH) → fraction=0.0.
    """
    problems = (
        [_ps("alpha", 0, "HIGH"), _ps("alpha", 1, "LOW")]
        + [_ps("beta", i, "LOW") for i in range(5)]
    )
    result = severity_concentration_report(problems, "HIGH", 0.4)
    alpha = result["alpha"]
    assert abs(alpha["fraction"] - 0.5) < 1e-9, (
        "alpha: 1/2=0.5; got " + repr(alpha["fraction"])
    )
    beta = result["beta"]
    assert beta["fraction"] == 0.0, (
        "beta: 0/5=0.0; got " + repr(beta["fraction"])
    )


def test_exceeds_threshold_uses_inclusive_ge_boundary() -> None:
    """exceeds_threshold is True when fraction exactly equals min_fraction (>= boundary).

    Kills impl using strictly > which would return False at equality.
    alpha: 1/2=0.5.  min_fraction=0.5 → exceeds_threshold=True.
    """
    problems = [_ps("alpha", 0, "HIGH"), _ps("alpha", 1, "LOW")]
    result = severity_concentration_report(problems, "HIGH", 0.5)
    assert result["alpha"]["exceeds_threshold"] is True, (
        "fraction=0.5 >= min_fraction=0.5 → True; got "
        + repr(result["alpha"]["exceeds_threshold"])
    )


def test_classes_with_zero_at_severity_still_included() -> None:
    """Classes with no problems at the target severity appear with at_severity=0.

    Kills impl that skips classes without the target severity.
    beta has only LOW problems; asking for HIGH → beta included with at_severity=0.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("beta", 0, "LOW"),
    ]
    result = severity_concentration_report(problems, "HIGH", 0.5)
    assert "beta" in result, "beta must appear (with at_severity=0)"
    assert result["beta"]["at_severity"] == 0, (
        "beta has no HIGH → at_severity=0; got " + repr(result["beta"]["at_severity"])
    )
    assert result["beta"]["fraction"] == 0.0


def test_empty_input_returns_empty_dict() -> None:
    """Empty input → {}.

    Kills impl that raises on empty input.
    """
    result = severity_concentration_report([], "HIGH", 0.5)
    assert result == {}, "Empty input → {}; got " + repr(result)
