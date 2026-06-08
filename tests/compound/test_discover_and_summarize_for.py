"""Item 167: discover_and_summarize_for() — TIDE pipeline with class filter (2026-06-08).

``discover_and_summarize_for(paths, *, templates=None, exclude_known=frozenset(),
problem_classes=None)`` → ``ProblemSummary``: extends :func:`discover_and_summarize`
with an optional post-discovery class filter.  When ``problem_classes`` is provided,
only :class:`Problem` instances whose ``problem_class`` is in ``problem_classes`` are
passed to :func:`problem_summary`.  Filtering happens AFTER the full discovery run —
all instruments run regardless of the filter.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: ``problem_classes`` applied to a multi-class result → ``total`` and
     ``by_class`` cover ONLY that class.  Kills an impl that filters the TEMPLATE LIST
     instead of the FINDINGS LIST (which would skip instruments, not findings).
  2. ``problem_classes=None`` → identical result to ``discover_and_summarize`` for the
     same arguments.  Kills an impl that always applies filtering even when None.
  3. Empty ``problem_classes=set()`` → ``total=0``.
     Kills an impl that treats empty set as "no filter" (pass-through).
  4. Multiple classes in filter → only those classes appear in ``by_class``.
     Kills an impl that uses startswith/subset logic incorrectly.
  5. Returns a frozen ``ProblemSummary`` instance.
     Kills an impl that returns a list of Problems instead of wrapping in ProblemSummary.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from cohezion.compound.problem_discovery import (
    ProblemSummary,
    ProblemTemplate,
    discover_and_summarize,
    discover_and_summarize_for,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _template(cls: str, n: int = 2) -> ProblemTemplate:
    """Stub template that always returns ``n`` findings of class ``cls``."""

    def _instrument(paths: list[Path]) -> list:
        return [f"{cls}_finding_{i}" for i in range(n)]

    return ProblemTemplate(
        problem_class=cls,
        instrument=_instrument,
        key=str,
    )


# Two stubs: alpha (3 findings) and beta (2 findings)
ALPHA = _template("alpha", n=3)
BETA = _template("beta", n=2)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_class_filter_restricts_findings() -> None:
    """problem_classes={"alpha"} → total covers ONLY alpha findings.

    PRIMARY DISCRIMINATOR: kills an impl that filters the template list
    (which would skip running the beta instrument entirely, meaning the call
    would raise or return an incorrect result depending on interaction with
    exclude_known).

    Uses two stub templates (alpha=3, beta=2). With filter={"alpha"}: total=3.
    Without filter: total=5. The difference proves filtering is post-discovery.
    """
    paths: list[Path] = []
    templates = [ALPHA, BETA]

    summary_all = discover_and_summarize_for(paths, templates=templates)
    summary_alpha_only = discover_and_summarize_for(
        paths,
        templates=templates,
        problem_classes={"alpha"},
    )

    assert summary_all.total == 5, (
        f"Unfiltered should have alpha(3)+beta(2)=5; got {summary_all.total}"
    )
    assert summary_alpha_only.total == 3, (
        f"Filtered to alpha only should have total=3; got {summary_alpha_only.total}"
    )
    assert list(summary_alpha_only.by_class.keys()) == ["alpha"], (
        f"by_class must contain ONLY 'alpha'; got {summary_alpha_only.by_class}"
    )
    assert "beta" not in summary_alpha_only.by_class, (
        "beta must be absent from by_class after filtering"
    )


def test_none_filter_equals_discover_and_summarize() -> None:
    """problem_classes=None → same result as discover_and_summarize.

    Kills an impl that always applies filtering even when problem_classes is None
    (would produce total=0 for every call, silently discarding all findings).
    """
    paths: list[Path] = []
    templates = [ALPHA, BETA]

    expected = discover_and_summarize(paths, templates=templates)
    result = discover_and_summarize_for(paths, templates=templates, problem_classes=None)

    assert result.total == expected.total, (
        f"problem_classes=None must match discover_and_summarize; "
        f"got {result.total} vs {expected.total}"
    )
    assert result.by_class == expected.by_class, (
        f"by_class must match; got {result.by_class} vs {expected.by_class}"
    )


def test_empty_problem_classes_yields_zero() -> None:
    """problem_classes=set() (empty) → total=0, has_problems=False.

    Kills an impl that treats empty set as 'no filter' and passes all findings
    through (which would make this test fail with total=5).
    """
    paths: list[Path] = []
    templates = [ALPHA, BETA]

    summary = discover_and_summarize_for(
        paths,
        templates=templates,
        problem_classes=set(),
    )

    assert summary.total == 0, f"Empty problem_classes must yield total=0; got {summary.total}"
    assert summary.has_problems is False


def test_multiple_classes_in_filter() -> None:
    """problem_classes={alpha, beta} → both classes appear in by_class.

    Kills an impl that only handles single-class filters (e.g., checks
    problem_classes == {single_value} rather than `in problem_classes`).
    """
    paths: list[Path] = []
    templates = [ALPHA, BETA]

    summary = discover_and_summarize_for(
        paths,
        templates=templates,
        problem_classes={"alpha", "beta"},
    )

    assert summary.total == 5, f"Both classes present: alpha(3)+beta(2)=5; got {summary.total}"
    assert "alpha" in summary.by_class, "alpha must be in by_class"
    assert "beta" in summary.by_class, "beta must be in by_class"


def test_returns_frozen_problem_summary() -> None:
    """discover_and_summarize_for returns a frozen ProblemSummary.

    Kills an impl that returns a list of Problems or a mutable dict.
    """
    summary = discover_and_summarize_for([], templates=[ALPHA])

    assert isinstance(summary, ProblemSummary), f"Expected ProblemSummary; got {type(summary)}"
    try:
        summary.total = 999  # type: ignore[misc]
        raise AssertionError("FrozenInstanceError not raised")
    except dataclasses.FrozenInstanceError:
        pass  # expected
