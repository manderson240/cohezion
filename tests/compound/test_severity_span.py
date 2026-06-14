"""Item 335: severity_span() — count of distinct labelled severity levels per class (2026-06-08).

``severity_span(problems) -> dict[str, int]``:
Returns {class_name: distinct_severity_count} for all classes with >=1 labelled problem.
Unlabelled-only classes excluded.  Empty -> {}.  Pure; no I/O.

Quantified form of multi_severity_classes: span=1 = homogeneous, span>=2 = heterogeneous.
Multi_severity_classes(p) == {cls for cls, span in severity_span(p).items() if span >= 2}.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: class with 3 distinct severities has span=3 (not 1 or bool).
     Kills impl returning 1 or a boolean.
  2. Class with all problems at ONE severity has span=1 (not 0 or missing).
     Kills impl off-by-one or using record count.
  3. Unlabelled-only class is excluded (no key in result).
     Kills impl treating unlabelled as a severity.
  4. Empty input returns {}.
     Kills impl raising on empty.
  5. span values match multi/single_severity_classes: span>=2 iff in multi, span==1 iff in single.
     Kills impl with incorrect boundary classification.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    multi_severity_classes,
    severity_span,
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


def test_class_with_three_severities_has_span_three() -> None:
    """Class with 3 distinct severities reports span=3.

    PRIMARY DISCRIMINATOR: kills impl returning 1 or bool.
    alpha: CRITICAL + HIGH + LOW (3 severities) -> span=3.
    """
    problems = [
        _ps("alpha", 0, "CRITICAL"),
        _ps("alpha", 1, "HIGH"),
        _ps("alpha", 2, "LOW"),
    ]
    result = severity_span(problems)
    assert result.get("alpha") == 3, "alpha has 3 distinct severities -> span=3; got " + repr(
        result.get("alpha")
    )


def test_class_with_one_severity_has_span_one() -> None:
    """Class with all problems at a single severity has span=1.

    Kills impl using record count instead of distinct severity count.
    alpha: 5 HIGH records -> span=1 (not 5).
    """
    problems = [_ps("alpha", i, "HIGH") for i in range(5)]
    result = severity_span(problems)
    assert result.get("alpha") == 1, "5 HIGH records -> span=1 (distinct count); got " + repr(
        result.get("alpha")
    )


def test_unlabelled_only_class_excluded() -> None:
    """Class with only unlabelled problems has no key in result.

    Kills impl treating unlabelled (severity='') as a severity.
    """
    problems = [_p("alpha", 0), _p("alpha", 1)]
    result = severity_span(problems)
    assert "alpha" not in result, "alpha has only unlabelled -> not in span result; got " + repr(
        result
    )


def test_empty_input_returns_empty_dict() -> None:
    """Empty input returns {} without raising."""
    assert severity_span([]) == {}, "empty -> {}; got " + repr(severity_span([]))


def test_span_consistent_with_multi_and_single() -> None:
    """span >= 2 iff in multi_severity_classes; span == 1 iff in single.

    Kills impl with incorrect boundary classification.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "LOW"),  # span=2 -> multi
        _ps("beta", 0, "HIGH"),
        _ps("beta", 1, "HIGH"),  # span=1 -> single
        _p("gamma", 0),  # unlabelled -> neither
    ]
    spans = severity_span(problems)
    multi = multi_severity_classes(problems)
    single = single_severity_classes(problems)
    for cls, span in spans.items():
        if span >= 2:
            assert cls in multi, f"{cls} span={span} -> must be in multi; multi={multi}"
        elif span == 1:
            assert cls in single, f"{cls} span={span} -> must be in single; single={single}"
    assert "gamma" not in spans, "unlabelled-only gamma not in spans"
