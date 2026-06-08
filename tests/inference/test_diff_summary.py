"""Item 166: diff_summary() — human-readable TournamentSnapshotDiff report (2026-06-08).

``diff_summary(diff)`` → ``str``: given a :class:`TournamentSnapshotDiff`, returns a
compact multi-line report listing what changed between two tournament snapshots.

  - Empty diff (equal snapshots, all partitions empty or only unchanged) → ``"No changes."``
  - Added winners appear with their new ``model_id``.
  - Removed winners are listed by task value.
  - Changed entries show both the old and new ``model_id``.
  - Unchanged entries are NOT listed (they are stable — no audit interest).

Pure string fold; no I/O, no SurrealDB.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: Non-trivial diff (added task) → report contains the task name AND
     the new model_id.  Kills an impl that always returns ``"No changes."``.
  2. Equal snapshots (only unchanged, all other partitions empty) → ``"No changes."``.
     Kills an impl that lists all tasks as unchanged verbosely.
  3. Removed task appears in the report.
     Kills an impl that omits the removed partition.
  4. Changed entry shows BOTH old and new model_id.
     Kills an impl that reports only the new model (losing the audit trail).
  5. Unchanged partition is NOT mentioned in the report.
     Kills an impl that verbosely logs stable tasks (cluttering the audit log).
"""

from __future__ import annotations

from cohezion.inference.registry import Task
from cohezion.inference.tournament_deposit import (
    TournamentSnapshotDiff,
    diff_summary,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _diff(
    *,
    added: dict[str, str] | None = None,
    removed: set[str] | None = None,
    changed: dict[str, tuple[str, str]] | None = None,
    unchanged: set[str] | None = None,
) -> TournamentSnapshotDiff:
    return TournamentSnapshotDiff(
        added=added or {},
        removed=removed or set(),
        changed=changed or {},
        unchanged=unchanged or set(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_added_task_appears_with_model() -> None:
    """A new winner in the added partition → report contains task name AND model_id.

    PRIMARY DISCRIMINATOR: kills an impl that always returns 'No changes.'.
    Also kills an impl that reports the task but omits the model_id.
    """
    diff = _diff(added={Task.CODE_GEN.value: "qwen3-coder"})
    report = diff_summary(diff)

    assert Task.CODE_GEN.value in report, f"Added task name must appear in report; got:\n{report!r}"
    assert "qwen3-coder" in report, f"New model_id must appear in report; got:\n{report!r}"
    assert report != "No changes.", "Non-empty diff must not return 'No changes.'"


def test_equal_snapshots_returns_no_changes() -> None:
    """Equal snapshots (unchanged partition only) → exactly 'No changes.'.

    Kills an impl that verbosely lists stable winners (unchanged partition).
    The unchanged partition is audit-noise — only deltas matter.
    """
    diff = _diff(unchanged={Task.CODE_GEN.value, Task.SUMMARIZATION.value})
    report = diff_summary(diff)

    assert report == "No changes.", (
        f"Equal snapshots (only unchanged) must return 'No changes.'; got {report!r}"
    )


def test_removed_task_appears_in_report() -> None:
    """Removed task (in before but not after) → task name appears in report.

    Kills an impl that omits the removed partition from the output.
    """
    diff = _diff(removed={Task.SUMMARIZATION.value})
    report = diff_summary(diff)

    assert Task.SUMMARIZATION.value in report, (
        f"Removed task must appear in report; got:\n{report!r}"
    )
    assert report != "No changes.", "Non-empty diff must not return 'No changes.'"


def test_changed_entry_shows_both_old_and_new_model() -> None:
    """Changed entry → report contains BOTH old_model AND new_model.

    Kills an impl that shows only the new model (losing the audit trail of what
    was replaced, which is critical for rollback decisions).
    """
    diff = _diff(changed={Task.CODE_GEN.value: ("OldModel-7B", "NewModel-12B")})
    report = diff_summary(diff)

    assert "OldModel-7B" in report, (
        f"Old model_id must appear in report for changed entry; got:\n{report!r}"
    )
    assert "NewModel-12B" in report, (
        f"New model_id must appear in report for changed entry; got:\n{report!r}"
    )
    assert Task.CODE_GEN.value in report, (
        f"Changed task name must appear in report; got:\n{report!r}"
    )


def test_unchanged_partition_not_mentioned() -> None:
    """Unchanged tasks are NOT listed in the report (they are stable — no audit interest).

    Kills an impl that verbosely appends an 'unchanged: [task1, task2, ...]' section,
    which would clutter the audit log with noise on every scan.
    A diff report is for WHAT CHANGED, not what stayed the same.
    """
    diff = _diff(
        added={Task.CODE_GEN.value: "new-model"},
        unchanged={Task.SUMMARIZATION.value},
    )
    report = diff_summary(diff)

    # The added task must appear, the unchanged one must NOT
    assert Task.CODE_GEN.value in report, "Added task must appear"
    assert Task.SUMMARIZATION.value not in report, (
        f"Unchanged task must NOT appear in report (audit noise); got:\n{report!r}"
    )


def test_empty_diff_all_partitions_empty() -> None:
    """All partitions empty → 'No changes.'.

    This is the purest form of the 'no changes' case — nothing in any partition.
    Kills an impl that checks for non-empty unchanged partition before returning
    'No changes.' (the empty diff has no unchanged either).
    """
    diff = _diff()
    report = diff_summary(diff)

    assert report == "No changes.", f"Empty diff must return 'No changes.'; got {report!r}"
