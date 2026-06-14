"""Item 317: severity_density_by_class() — within-class severity fractions (2026-06-08).

``severity_density_by_class(problems) -> dict[str, dict[str, float]]``:
Returns nested dict: outer=class, inner=severity, value=count(class,sev)/count(class).
Denominator is each class's TOTAL problems (not global total).
Unlabelled excluded from inner dict.  Classes with no labelled problems omitted.
Empty -> {}.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: denominator = count(class) not count(all problems).
     Kills impl using global total as denominator.
  2. Values per class sum to <= 1.0 (strictly < 1.0 when unlabelled exist).
     Kills impl where values sum to > 1.0.
  3. Unlabelled problems excluded from inner dict.
     Kills impl including '' key.
  4. Class with ONLY unlabelled problems NOT in result.
     Kills impl including classes with no labelled records.
  5. Empty problems -> {}.
     Kills impl raising on empty input.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_density_by_class,
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


def test_denominator_is_class_total_not_global() -> None:
    """Fractions use each class's own total, not the global total.

    PRIMARY DISCRIMINATOR: kills impl dividing by global total.
    alpha: 2 HIGH, 2 total -> HIGH fraction = 2/2 = 1.0.
    beta: 1 HIGH, 3 total -> HIGH fraction = 1/3 ≈ 0.333.
    If denominator were global (5): alpha HIGH = 2/5 = 0.4 (WRONG).
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "HIGH"),  # alpha: 2 HIGH / 2 total
        _ps("beta", 0, "HIGH"),
        _p("beta", 1),
        _p("beta", 2),  # beta: 1 HIGH / 3 total
    ]
    result = severity_density_by_class(problems)
    assert abs(result.get("alpha", {}).get("HIGH", -1) - 1.0) < 1e-9, "alpha: 2/2=1.0; got " + repr(
        result.get("alpha")
    )
    assert abs(result.get("beta", {}).get("HIGH", -1) - 1.0 / 3.0) < 1e-9, (
        "beta: 1/3≈0.333; got " + repr(result.get("beta"))
    )


def test_per_class_fractions_sum_at_most_one() -> None:
    """Sum of a class's severity fractions is <= 1.0.

    Kills impl summing to > 1.0.
    alpha: 1 HIGH, 1 LOW, 2 unlabelled -> total=4; HIGH=0.25, LOW=0.25, sum=0.5.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "LOW"),
        _p("alpha", 2),
        _p("alpha", 3),
    ]
    result = severity_density_by_class(problems)
    alpha_fracs = result.get("alpha", {})
    total = sum(alpha_fracs.values())
    assert total <= 1.0 + 1e-9, "Sum of fracs <= 1.0; got " + repr(total)
    assert abs(total - 0.5) < 1e-9, "alpha labelled fraction = 0.5; got " + repr(total)


def test_unlabelled_excluded_from_inner_dict() -> None:
    """Unlabelled problems (severity='') do not appear as a key.

    Kills impl including '' in inner dict.
    alpha: 1 HIGH, 1 unlabelled -> inner has only 'HIGH'.
    """
    problems = [_ps("alpha", 0, "HIGH"), _p("alpha", 1)]
    result = severity_density_by_class(problems)
    assert "alpha" in result, "alpha in result; got " + repr(result)
    assert "" not in result["alpha"], "'' must not be a key; got " + repr(result["alpha"])


def test_class_with_only_unlabelled_omitted() -> None:
    """Class with only unlabelled problems not in result.

    Kills impl including classes with no labelled records.
    beta: only unlabelled -> NOT in result.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _p("beta", 0),
        _p("beta", 1),
    ]
    result = severity_density_by_class(problems)
    assert "alpha" in result, "alpha has labelled problems; got " + repr(result)
    assert "beta" not in result, "beta only unlabelled -> NOT in result; got " + repr(result)


def test_empty_problems_returns_empty_dict() -> None:
    """Empty problems -> {} without raising.

    Kills impl raising on empty input.
    """
    result = severity_density_by_class([])
    assert result == {}, "Empty -> {}; got " + repr(result)
