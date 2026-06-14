"""Item 437: severity_entropy() -- Shannon entropy of the severity distribution (2026-06-08).

``severity_entropy(problems) -> float``:
Returns H = -sum(p * log2(p)) over severity_coverage_ratio values.
Two equal severities -> 1.0.  Single severity -> 0.0.  Empty -> 0.0.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on severity histogram (not class/fid distribution).
     Kills impl reusing class_entropy or finding_id_entropy (wrong field).
  2. Two equal severities -> 1.0 bit (log2, not ln).
     Kills impl using natural log (would give ln(2) ~= 0.693).
  3. Single severity -> 0.0 (certain outcome, no diversity).
     Validates degenerate case.
  4. Empty -> 0.0 (not ZeroDivisionError).
     Kills impl with unguarded division.
  5. Unequal severity distribution -> correct entropy value.
     Validates general formula.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_entropy,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_keyed_on_severity_not_class() -> None:
    """Entropy is over severity distribution, not class distribution.

    PRIMARY DISCRIMINATOR: kills impl reusing class_entropy.
    Two classes but one severity -> severity_entropy=0.0, class_entropy=1.0.
    """
    problems = [
        _p("alpha", "f1", "HIGH"),
        _p("beta", "f2", "HIGH"),  # same severity, different class
    ]
    result = severity_entropy(problems)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # Both have 'HIGH' severity -> single severity -> H=0.0
    # class_entropy would be 1.0 (two equal classes)
    assert abs(result - 0.0) < 1e-9, "Single severity 'HIGH' -> 0.0; got " + repr(result)


def test_two_equal_severities_returns_one_bit() -> None:
    """Two equal-frequency severities -> H = 1.0 bit (log2, not ln)."""
    problems = [_p("cls", "f1", "HIGH"), _p("cls", "f2", "LOW")]
    result = severity_entropy(problems)
    assert abs(result - 1.0) < 1e-9, "Two equal severities -> 1.0 bit; got " + repr(result)


def test_single_severity_returns_zero() -> None:
    """Single severity -> H = 0.0 (certain outcome)."""
    problems = [_p("a", "f1", "CRITICAL"), _p("b", "f2", "CRITICAL")]
    result = severity_entropy(problems)
    assert abs(result - 0.0) < 1e-9, "Single severity -> 0.0; got " + repr(result)


def test_empty_returns_zero() -> None:
    """Empty input returns 0.0, not ZeroDivisionError."""
    result = severity_entropy([])
    assert result == 0.0, "Empty -> 0.0; got " + repr(result)
    assert isinstance(result, float)


def test_unequal_severity_distribution_correct_entropy() -> None:
    """Unequal severity distribution returns correct Shannon entropy.

    HIGH=2/4=1/2, LOW=1/4, MEDIUM=1/4.
    H = -(1/2*log2(1/2) + 1/4*log2(1/4) + 1/4*log2(1/4))
      = -(−0.5 + −0.5 + −0.5) = 1.5 bits
    """
    problems = [
        _p("cls", "f1", "HIGH"),
        _p("cls", "f2", "HIGH"),
        _p("cls", "f3", "LOW"),
        _p("cls", "f4", "MEDIUM"),
    ]
    result = severity_entropy(problems)
    assert abs(result - 1.5) < 1e-9, "H should be 1.5 bits; got " + repr(result)
