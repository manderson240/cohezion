"""Item 173: problem_diff_summary() — human-readable audit log for a ProblemDiff (2026-06-08).

``problem_diff_summary(diff: ProblemDiff)`` → ``str``:
Returns a compact multi-line string listing added and resolved finding ids.
Identical scans (all-stable diff) → ``"No changes."``.

Mirrors :func:`cohezion.inference.tournament_deposit.diff_summary` (item 166)
but for code-smell :class:`ProblemDiff` instances instead of tournament snapshots.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: non-empty diff → string contains counts and ids of added + resolved.
     Kills an impl that returns an empty string or "No changes." for any diff.
  2. Identical inputs (all-stable, no adds/resolved) → exactly ``"No changes."``.
     Kills an impl that always includes a non-empty added/resolved section.
  3. Added-only diff → "resolved" label absent from the string.
     Kills an impl that always emits a resolved section (empty or not).
  4. Resolved-only diff → "added" label absent from the string.
     Kills an impl that always emits an added section (empty or not).
  5. Both added and resolved → both sections present in the string.
     Kills an impl that only emits the first non-empty partition.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    ProblemDiff,
    problem_diff_summary,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _diff(
    added: list[str] | None = None,
    resolved: list[str] | None = None,
    stable: list[str] | None = None,
) -> ProblemDiff:
    return ProblemDiff(
        added=added or [],
        resolved=resolved or [],
        stable=stable or [],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_nonempty_diff_contains_added_and_resolved_info() -> None:
    """Non-empty diff (both added and resolved) → string mentions both.

    PRIMARY DISCRIMINATOR: kills an impl that returns '' or 'No changes.'
    for any non-empty diff — would hide real findings from the operator.
    """
    diff = _diff(
        added=["complexity_outlier:foo.py:10"],
        resolved=["nesting_outlier:bar.py:5"],
    )

    result = problem_diff_summary(diff)

    assert result != "No changes.", f"Non-empty diff must not return 'No changes.'; got {result!r}"
    assert "complexity_outlier:foo.py:10" in result, (
        f"Added id must appear in summary; got {result!r}"
    )
    assert "nesting_outlier:bar.py:5" in result, (
        f"Resolved id must appear in summary; got {result!r}"
    )


def test_all_stable_returns_no_changes() -> None:
    """No added, no resolved (identical scans) → exactly 'No changes.'.

    Kills an impl that always emits a non-empty string (e.g., a header line)
    even when there is nothing to report.
    """
    diff = _diff(stable=["compound_smell:baz.py:1"])

    result = problem_diff_summary(diff)

    assert result == "No changes.", f"All-stable diff must return 'No changes.'; got {result!r}"


def test_added_only_diff_does_not_mention_resolved() -> None:
    """added-only diff → 'resolved' label absent from the string.

    Kills an impl that always emits a resolved section (even empty), which
    would produce misleading output like 'resolved: (none)'.
    """
    diff = _diff(added=["long_function:qux.py:20"])

    result = problem_diff_summary(diff)

    # The word "resolved" must not appear when nothing was resolved
    assert "resolved" not in result.lower(), (
        f"added-only diff must not mention 'resolved'; got {result!r}"
    )
    assert "long_function:qux.py:20" in result, f"Added id must appear in summary; got {result!r}"


def test_resolved_only_diff_does_not_mention_added() -> None:
    """resolved-only diff → 'added' label absent from the string.

    Kills an impl that always emits an added section (even empty).
    """
    diff = _diff(resolved=["passthrough_function:mod.py:3"])

    result = problem_diff_summary(diff)

    assert "added" not in result.lower(), (
        f"resolved-only diff must not mention 'added'; got {result!r}"
    )
    assert "passthrough_function:mod.py:3" in result, (
        f"Resolved id must appear in summary; got {result!r}"
    )


def test_both_sections_present_when_both_have_content() -> None:
    """Both added and resolved non-empty → both sections present.

    Kills an impl that short-circuits after the first non-empty partition,
    only emitting added when added is non-empty and resolved is also non-empty.
    """
    diff = _diff(
        added=["long_parameter_list:a.py:1", "mutable_default_args:b.py:2"],
        resolved=["boolean_flag_params:c.py:3"],
    )

    result = problem_diff_summary(diff)

    assert "long_parameter_list:a.py:1" in result, f"First added id must appear; got {result!r}"
    assert "mutable_default_args:b.py:2" in result, f"Second added id must appear; got {result!r}"
    assert "boolean_flag_params:c.py:3" in result, f"Resolved id must appear; got {result!r}"
