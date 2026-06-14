"""Item 174: problem_diff_pipeline() — end-to-end two-scan delta pipeline (2026-06-08).

``problem_diff_pipeline(paths_before, paths_after, *, templates=None,
exclude_known_before=frozenset(), exclude_known_after=frozenset())``
→ ``tuple[list[Problem], list[Problem], ProblemDiff, str]``:

Runs ``discover_problems`` on both path sets, calls ``problem_diff``, calls
``problem_diff_summary``.  Returns a 4-tuple ``(before, after, diff, summary)``.

Mirrors :func:`cohezion.inference.tournament_deposit.snapshot_pipeline` (item 168)
but for code-smell TIDE discovery instead of tournament snapshots.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: identical paths + same templates → summary=="No changes."
     AND diff.added==[].
     Kills an impl that forces a diff even for equal inputs.
  2. Different injected templates (different findings) → diff.added populated
     and summary contains a finding id from the new findings.
     Kills an impl that always returns the same before list as after.
  3. Return value is a 4-tuple in the exact order (before, after, diff, summary).
     Kills an impl that reorders elements or returns a dict/dataclass.
  4. First two elements are list[Problem] instances (not raw strings or dicts).
     Kills an impl that returns raw finding ids instead of typed Problem lists.
  5. Fourth element is str (the summary).
     Kills an impl that returns the ProblemDiff as the fourth element.
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.problem_discovery import (
    Problem,
    ProblemDiff,
    ProblemTemplate,
    problem_diff_pipeline,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_template(problem_class: str, finding_ids: list[str]) -> ProblemTemplate:
    """Injectable stub: emits fixed findings regardless of paths."""
    captured = [Problem(problem_class=problem_class, finding_id=fid) for fid in finding_ids]
    return ProblemTemplate(
        problem_class=problem_class,
        instrument=lambda _paths: captured,
        key=lambda p: p.finding_id,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_identical_inputs_produce_no_changes() -> None:
    """Same templates on both scans → summary=='No changes.' AND diff.added==[].

    PRIMARY DISCRIMINATOR: kills an impl that always forces a diff even for
    equal inputs (e.g., one that always puts all findings in diff.added).
    """
    templates = [_make_template("complexity_outlier", ["mod.py:10", "mod.py:20"])]

    _before, _after, diff, summary = problem_diff_pipeline(
        [Path(".")],
        [Path(".")],
        templates=templates,
    )

    assert summary == "No changes.", f"Identical inputs must produce 'No changes.'; got {summary!r}"
    assert diff.added == [], f"Identical inputs must have empty added; got {diff.added!r}"
    assert diff.resolved == [], f"Identical inputs must have empty resolved; got {diff.resolved!r}"


def test_different_exclude_known_shows_added_findings() -> None:
    """exclude_known_before suppresses a finding in before → appears in diff.added.

    Kills an impl that always returns the before list as after (no real second scan).
    The same templates produce the same findings; exclude_known_before hides the id
    from the before scan so the after scan (which sees it) reports it as 'added'.
    """
    finding_id = "complexity_outlier:new.py:99"
    templates = [_make_template("complexity_outlier", ["new.py:99"])]

    _before, _after, diff, summary = problem_diff_pipeline(
        [Path(".")],
        [Path(".")],
        templates=templates,
        exclude_known_before={finding_id},  # suppress in before → appears as "added"
    )

    assert finding_id in diff.added, (
        f"Finding suppressed in before must appear in diff.added; got {diff.added!r}"
    )
    assert finding_id in summary, f"Added finding id must appear in summary; got {summary!r}"


def test_return_is_four_tuple() -> None:
    """Return value is a 4-tuple (before, after, diff, summary).

    Kills an impl that returns a dict, a 3-tuple, or a named dataclass.
    """
    result = problem_diff_pipeline([Path(".")], [Path(".")], templates=[])

    assert isinstance(result, tuple), f"Expected tuple; got {type(result)}"
    assert len(result) == 4, f"Expected 4-tuple; got len={len(result)}"


def test_first_two_elements_are_problem_lists() -> None:
    """before and after are list[Problem] instances.

    Kills an impl that returns raw finding id strings or plain dicts.
    """
    templates = [_make_template("long_function", ["f.py:1"])]
    before, after, _diff, _summary = problem_diff_pipeline(
        [Path(".")], [Path(".")], templates=templates
    )

    assert isinstance(before, list), f"before must be list; got {type(before)}"
    assert isinstance(after, list), f"after must be list; got {type(after)}"
    if before:
        assert isinstance(before[0], Problem), (
            f"before elements must be Problem; got {type(before[0])}"
        )
    if after:
        assert isinstance(after[0], Problem), (
            f"after elements must be Problem; got {type(after[0])}"
        )


def test_fourth_element_is_str_diff_is_problem_diff() -> None:
    """Third element is ProblemDiff, fourth is str (summary).

    Kills an impl that swaps the diff and summary positions or returns the
    ProblemDiff as the fourth element.
    """
    _before, _after, diff, summary = problem_diff_pipeline([Path(".")], [Path(".")], templates=[])

    assert isinstance(diff, ProblemDiff), f"Third element must be ProblemDiff; got {type(diff)}"
    assert isinstance(summary, str), f"Fourth element must be str (summary); got {type(summary)}"
