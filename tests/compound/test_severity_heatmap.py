"""Item 308: severity_heatmap() — full class × severity count matrix (2026-06-08).

``severity_heatmap(problems: list[Problem]) -> dict[str, dict[str, int]]``:
Returns nested dict: outer key = class name, inner key = severity label,
value = count of problems with that class+severity.  Only labelled problems
(severity \!= '') contribute.  Classes with zero labelled problems are omitted.
Empty -> {}.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: inner dict only contains severities with count >= 1.
     Kills impl pre-populating all severity labels with zero counts.
  2. Class with ONLY unlabelled problems -> NOT in result.
     Kills impl including classes with only empty-severity problems.
  3. Two classes -> two outer keys with correct inner counts.
     Kills impl merging counts across classes.
  4. Single labelled problem -> {class: {severity: 1}}.
     Kills impl off-by-one on count.
  5. Empty problems -> {}.
     Kills impl raising on empty input.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_heatmap,
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


def test_inner_dict_only_contains_severities_with_nonzero_count() -> None:
    """Inner dict only includes severities that actually appear, count >= 1.

    PRIMARY DISCRIMINATOR: kills impl pre-populating all severity slots.
    alpha: 2 HIGH, 1 LOW -> inner = {"HIGH": 2, "LOW": 1}.
    "CRITICAL" not present -> must NOT be a key in inner dict.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "HIGH"),
        _ps("alpha", 2, "LOW"),
    ]
    result = severity_heatmap(problems)
    assert "alpha" in result, "alpha has labelled problems; got " + repr(result)
    assert result["alpha"] == {"HIGH": 2, "LOW": 1}, "alpha inner = {HIGH:2, LOW:1}; got " + repr(
        result["alpha"]
    )
    assert "CRITICAL" not in result["alpha"], "CRITICAL not present -> no key; got " + repr(
        result["alpha"]
    )


def test_class_with_only_unlabelled_problems_omitted() -> None:
    """Class whose problems all have severity='' is NOT in result.

    Kills impl including classes with only unlabelled problems.
    beta: 3 unlabelled problems -> not in result.
    alpha: 1 HIGH -> in result.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _p("beta", 0),
        _p("beta", 1),
        _p("beta", 2),
    ]
    result = severity_heatmap(problems)
    assert "alpha" in result, "alpha has labelled problem; got " + repr(result)
    assert "beta" not in result, "beta only unlabelled -> NOT in result; got " + repr(result)


def test_two_classes_have_independent_inner_dicts() -> None:
    """Two classes produce two separate outer keys with correct counts.

    Kills impl merging counts across classes.
    alpha: HIGH=2. beta: HIGH=1, CRITICAL=1.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "HIGH"),
        _ps("beta", 0, "HIGH"),
        _ps("beta", 1, "CRITICAL"),
    ]
    result = severity_heatmap(problems)
    assert result.get("alpha") == {"HIGH": 2}, "alpha HIGH=2; got " + repr(result.get("alpha"))
    assert result.get("beta") == {"HIGH": 1, "CRITICAL": 1}, "beta HIGH=1,CRITICAL=1; got " + repr(
        result.get("beta")
    )


def test_single_labelled_problem_count_is_one() -> None:
    """Single labelled problem -> {class: {severity: 1}}, not 0 or 2.

    Kills impl with off-by-one error in counting.
    """
    problems = [_ps("alpha", 0, "HIGH")]
    result = severity_heatmap(problems)
    assert result == {"alpha": {"HIGH": 1}}, "Single problem -> {alpha: {HIGH: 1}}; got " + repr(
        result
    )


def test_empty_problems_returns_empty_dict() -> None:
    """Empty problems -> {} without raising.

    Kills impl raising on empty input.
    """
    result = severity_heatmap([])
    assert result == {}, "Empty -> {}; got " + repr(result)
