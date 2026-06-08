"""Item 171: discover_and_summarize_excluding() — TIDE summary with class exclusion guard
(2026-06-08).

``discover_and_summarize_excluding(paths, *, templates=None, exclude_known=frozenset(),
exclude_classes=frozenset(), n=5)`` → ``ProblemSummary``:

Composes ``discover_and_summarize`` with ``top_problem_classes_excluding`` so the
``top_classes`` field excludes caller-specified noisy classes.  ``total`` and ``by_class``
remain unaffected — they still reflect ALL findings.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: ``exclude_classes={"noisy"}`` where "noisy" is the top class →
     ``top_classes[0][0] != "noisy"``.
     Kills an impl that ignores ``exclude_classes`` in the ``top_classes`` field.
  2. ``by_class`` still contains "noisy" when "noisy" is excluded from ``top_classes``.
     Kills an impl that also removes excluded classes from ``by_class``.
  3. ``total`` is unchanged by exclusion.
     Kills an impl that drops excluded findings from the ``total`` count.
  4. ``exclude_classes=frozenset()`` → identical to ``discover_and_summarize``.
     Kills an impl that always applies filtering.
  5. All classes excluded → ``top_classes == []`` but ``total`` > 0.
     Kills an impl that raises instead of returning an empty top_classes list.
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.problem_discovery import (
    ProblemSummary,
    ProblemTemplate,
    discover_and_summarize,
    discover_and_summarize_excluding,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_templates(class_counts: dict[str, int]) -> list[ProblemTemplate]:
    """Build injectable stub templates: one per class, each emitting N findings."""
    templates = []
    for cls, count in class_counts.items():
        findings = [f"{cls}:{i}" for i in range(count)]
        templates.append(
            ProblemTemplate(
                problem_class=cls,
                instrument=lambda _paths, _f=findings: _f,
                key=lambda f: f,
            )
        )
    return templates


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_exclude_top_class_absent_from_top_classes() -> None:
    """exclude_classes={"noisy"} → "noisy" NOT in top_classes.

    PRIMARY DISCRIMINATOR: kills an impl that ignores exclude_classes when
    building the top_classes field of ProblemSummary.  "noisy" has 5 findings
    (the top class); it must be absent from top_classes but still present in
    by_class and counted in total.
    """
    templates = _make_templates({"noisy": 5, "alpha": 2, "beta": 1})

    summary = discover_and_summarize_excluding(
        [Path(".")],
        templates=templates,
        exclude_classes={"noisy"},
    )

    top_names = [cls for cls, _ in summary.top_classes]
    assert "noisy" not in top_names, f"'noisy' must be excluded from top_classes; got {top_names!r}"
    assert "alpha" in top_names, (
        f"'alpha' must appear in top_classes (not excluded); got {top_names!r}"
    )


def test_by_class_still_contains_excluded_class() -> None:
    """by_class is unaffected by exclude_classes — exclusion only alters top_classes.

    Kills an impl that also filters exclude_classes out of by_class (wrong:
    by_class must reflect ALL findings, not the filtered top-N).
    """
    templates = _make_templates({"noisy": 5, "alpha": 2})

    summary = discover_and_summarize_excluding(
        [Path(".")],
        templates=templates,
        exclude_classes={"noisy"},
    )

    assert "noisy" in summary.by_class, (
        f"by_class must still contain 'noisy' (exclusion only affects top_classes); "
        f"got {summary.by_class!r}"
    )
    assert summary.by_class["noisy"] == 5, (
        f"by_class['noisy'] must be 5; got {summary.by_class['noisy']!r}"
    )


def test_total_unchanged_by_exclusion() -> None:
    """total reflects ALL findings regardless of exclude_classes.

    Kills an impl that subtracts excluded findings from total (wrong: total
    is always len(all findings), the exclusion only reshapes top_classes).
    """
    templates = _make_templates({"noisy": 5, "alpha": 2, "beta": 1})

    summary = discover_and_summarize_excluding(
        [Path(".")],
        templates=templates,
        exclude_classes={"noisy"},
    )

    assert summary.total == 8, (
        f"total must be 8 (5+2+1), unchanged by exclusion; got {summary.total!r}"
    )


def test_empty_exclude_matches_discover_and_summarize() -> None:
    """exclude_classes=frozenset() → identical to discover_and_summarize.

    Kills an impl that always applies filtering even with an empty
    exclude_classes (the result must be identical to the non-excluding variant).
    """
    templates = _make_templates({"a": 3, "b": 2, "c": 1})
    paths = [Path(".")]

    expected = discover_and_summarize(paths, templates=templates)
    result = discover_and_summarize_excluding(
        paths,
        templates=templates,
        exclude_classes=frozenset(),
    )

    assert result.total == expected.total
    assert result.by_class == expected.by_class
    assert result.top_classes == expected.top_classes
    assert result.has_problems == expected.has_problems


def test_all_classes_excluded_top_classes_empty_total_nonzero() -> None:
    """All classes in exclude_classes → top_classes==[] but total>0.

    Kills an impl that raises when all classes are excluded, or one that
    incorrectly sets total=0 because every class was excluded.
    """
    templates = _make_templates({"alpha": 2, "beta": 3})

    summary = discover_and_summarize_excluding(
        [Path(".")],
        templates=templates,
        exclude_classes={"alpha", "beta"},
    )

    assert summary.top_classes == [], (
        f"All classes excluded → top_classes must be []; got {summary.top_classes!r}"
    )
    assert summary.total == 5, (
        f"total must be 5 (all findings still counted); got {summary.total!r}"
    )
    assert isinstance(summary, ProblemSummary), "Must return ProblemSummary, not raise"
