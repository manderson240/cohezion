"""Item 165: discover_and_summarize() — TIDE pipeline convenience wrapper (2026-06-08).

``discover_and_summarize(paths, *, templates=None, exclude_known=frozenset())`` →
``ProblemSummary``: composes ``discover_problems`` (item 73) and ``problem_summary``
(item 163) into a single call.  All ``discover_problems`` parameters pass through
unchanged.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: ``ProblemSummary.total == len(discover_problems(same_paths))``
     for the same arguments.  Kills an impl that re-runs discovery independently
     (a second run could diverge if templates are non-deterministic or include
     external state) — both calls must share a SINGLE discovery pass.
  2. Empty / template-less call → ``has_problems=False``, ``total=0``.
     Kills an impl that short-circuits the problem_summary step.
  3. ``exclude_known`` propagates: an excluded finding does NOT appear in the
     summary.  Kills an impl that ignores ``exclude_known`` and passes only
     ``paths`` to ``discover_problems``.
  4. ``templates=[]`` (empty registry) → ``total=0``, ``has_problems=False``.
     Kills an impl that ignores the ``templates`` kwarg.
  5. Returns a frozen ``ProblemSummary`` dataclass (not a dict/namespace).
     Kills an impl that returns a plain dict.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from cohezion.compound.problem_discovery import (
    ProblemSummary,
    ProblemTemplate,
    discover_and_summarize,
    discover_problems,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _always_two_findings(paths: list[Path]) -> list:
    """Stub instrument that always returns two findings regardless of paths."""
    return ["finding_a", "finding_b"]


def _empty_instrument(paths: list[Path]) -> list:
    """Stub instrument that always returns no findings."""
    return []


def _one_finding_instrument(paths: list[Path]) -> list:
    return ["f1"]


STUB_TEMPLATE = ProblemTemplate(
    problem_class="stub",
    instrument=_always_two_findings,
    key=lambda f: f,
)

EMPTY_TEMPLATE = ProblemTemplate(
    problem_class="empty_class",
    instrument=_empty_instrument,
    key=lambda f: f,
)

ONE_TEMPLATE = ProblemTemplate(
    problem_class="single",
    instrument=_one_finding_instrument,
    key=lambda f: f,
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_total_equals_discover_problems_len() -> None:
    """PRIMARY DISCRIMINATOR: total equals len(discover_problems(same args)).

    Kills an impl that re-runs discover_problems internally (divergence risk)
    or that counts differently from the raw list length.
    """
    paths: list[Path] = []
    templates = [STUB_TEMPLATE]

    summary = discover_and_summarize(paths, templates=templates)
    expected_count = len(discover_problems(paths, templates=templates))

    assert summary.total == expected_count, (
        f"total must equal len(discover_problems(same args)); "
        f"got {summary.total} vs {expected_count}"
    )
    assert summary.total == 2, f"STUB_TEMPLATE always produces 2 findings; got {summary.total}"


def test_empty_templates_yields_zero_total() -> None:
    """templates=[] (empty registry) → total=0, has_problems=False.

    Kills an impl that ignores the templates kwarg and runs default_templates.
    """
    summary = discover_and_summarize([Path(".")], templates=[])

    assert summary.total == 0, f"Empty templates → total=0; got {summary.total}"
    assert summary.has_problems is False, (
        f"Empty templates → has_problems=False; got {summary.has_problems}"
    )


def test_exclude_known_propagates() -> None:
    """exclude_known propagates to discover_problems: excluded finding absent from summary.

    Kills an impl that ignores exclude_known or only passes paths through.
    The stub template produces "stub:f1"; if exclude_known contains that id,
    total must be 0.
    """
    paths: list[Path] = []
    templates = [ONE_TEMPLATE]
    excluded_id = "single:f1"  # {problem_class}:{key(finding)}

    summary_without_exclusion = discover_and_summarize(paths, templates=templates)
    summary_with_exclusion = discover_and_summarize(
        paths, templates=templates, exclude_known={excluded_id}
    )

    assert summary_without_exclusion.total == 1, (
        f"Without exclusion: total must be 1; got {summary_without_exclusion.total}"
    )
    assert summary_with_exclusion.total == 0, (
        f"With exclusion: the only finding is excluded so total=0; "
        f"got {summary_with_exclusion.total}"
    )
    assert summary_with_exclusion.has_problems is False


def test_no_paths_empty_templates_zero_summary() -> None:
    """No paths + templates=[] → zero-total ProblemSummary.

    Kills an impl that short-circuits the problem_summary step and returns
    some non-summary object.
    """
    summary = discover_and_summarize([], templates=[])

    assert summary.total == 0
    assert summary.by_class == {}
    assert summary.top_classes == []
    assert summary.has_problems is False


def test_returns_frozen_problem_summary() -> None:
    """discover_and_summarize returns a frozen ProblemSummary dataclass.

    Kills an impl that returns a plain dict, a SimpleNamespace, or an
    unfrozen dataclass.
    """
    summary = discover_and_summarize([], templates=[STUB_TEMPLATE])

    assert isinstance(summary, ProblemSummary), f"Expected ProblemSummary; got {type(summary)}"
    # Frozen guard
    try:
        summary.total = 999  # type: ignore[misc]
        raise AssertionError("FrozenInstanceError not raised — dataclass is not frozen")
    except dataclasses.FrozenInstanceError:
        pass  # expected
