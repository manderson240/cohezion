"""Item 164: tournament_snapshot_diff() — diff between two TournamentSnapshots (2026-06-08).

``tournament_snapshot_diff(before, after)`` → ``TournamentSnapshotDiff``: compares
two :class:`TournamentSnapshot` instances and classifies each task winner into
one of four partitions:

  - ``added``:     tasks in *after* but NOT in *before* — new winners deposited
  - ``removed``:   task values in *before* but NOT in *after* — winners lost
  - ``changed``:   tasks in BOTH but with a DIFFERENT model_id — model_id changed
  - ``unchanged``: tasks in BOTH with the SAME model_id — stable winners

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: A task in *after* but NOT in *before* lands in ``added``,
     NOT in ``changed``.  Kills impl that treats all "newly present" tasks as
     changed (the most common wrong approach).
  2. A task in *before* but NOT in *after* lands in ``removed``.
     Kills impl that drops removed tasks entirely.
  3. A task in both with a DIFFERENT model → ``changed``.
     Kills impl that ignores model_id changes.
  4. A task in both with the SAME model → ``unchanged``.
     Kills impl that includes stable tasks in ``changed`` or ``added``.
  5. Two equal snapshots → ``added={}``, ``removed=set()``, ``changed={}``,
     ``unchanged==set(after.winners.keys())``.
     Kills impl that always produces non-empty ``added`` or ``changed``.
"""

from __future__ import annotations

from cohezion.inference.registry import Task
from cohezion.inference.tournament_deposit import (
    TournamentSnapshot,
    tournament_snapshot_diff,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _snap(**winners: str) -> TournamentSnapshot:
    """Build a TournamentSnapshot directly from keyword task-value → model_id pairs."""
    d = dict(winners.items())
    return TournamentSnapshot(winners=d, task_count=len(d))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_added_not_changed_for_new_task() -> None:
    """A task in after but NOT in before → added, NOT changed.

    PRIMARY DISCRIMINATOR: kills impl that puts newly present tasks in
    ``changed`` instead of ``added``.
    """
    before = _snap()
    after = _snap(**{Task.CODE_GEN.value: "qwen3-coder"})

    diff = tournament_snapshot_diff(before, after)

    assert Task.CODE_GEN.value in diff.added, (
        f"CODE_GEN must be in added (new winner); got added={diff.added!r}"
    )
    assert Task.CODE_GEN.value not in diff.changed, (
        "CODE_GEN must NOT be in changed (it's newly added, not model-flipped)"
    )
    assert diff.added[Task.CODE_GEN.value] == "qwen3-coder", (
        f"added value must be the new model_id; got {diff.added.get(Task.CODE_GEN.value)!r}"
    )


def test_removed_for_task_dropped_from_after() -> None:
    """A task in before but NOT in after → removed.

    Kills impl that silently drops removed tasks (returns empty ``removed`` set).
    """
    before = _snap(**{Task.SUMMARIZATION.value: "phi3-mini"})
    after = _snap()  # SUMMARIZE winner no longer present

    diff = tournament_snapshot_diff(before, after)

    assert Task.SUMMARIZATION.value in diff.removed, (
        f"SUMMARIZE must be in removed; got removed={diff.removed!r}"
    )
    assert Task.SUMMARIZATION.value not in diff.added
    assert Task.SUMMARIZATION.value not in diff.changed


def test_changed_for_model_flip() -> None:
    """A task in both before and after with a DIFFERENT model → changed.

    Kills impl that ignores model_id changes (puts the task in ``unchanged``).
    """
    before = _snap(**{Task.CODE_GEN.value: "OldModel-7B"})
    after = _snap(**{Task.CODE_GEN.value: "NewModel-12B"})

    diff = tournament_snapshot_diff(before, after)

    assert Task.CODE_GEN.value in diff.changed, (
        f"CODE_GEN must be in changed (model flipped); got changed={diff.changed!r}"
    )
    old, new = diff.changed[Task.CODE_GEN.value]
    assert old == "OldModel-7B", f"old model must be 'OldModel-7B'; got {old!r}"
    assert new == "NewModel-12B", f"new model must be 'NewModel-12B'; got {new!r}"
    assert Task.CODE_GEN.value not in diff.unchanged


def test_unchanged_for_stable_winner() -> None:
    """A task in both with the SAME model → unchanged.

    Kills impl that includes stable tasks in changed or added.
    """
    before = _snap(**{Task.CODE_GEN.value: "stable-model"})
    after = _snap(**{Task.CODE_GEN.value: "stable-model"})

    diff = tournament_snapshot_diff(before, after)

    assert Task.CODE_GEN.value in diff.unchanged, (
        f"CODE_GEN must be in unchanged (same model); got unchanged={diff.unchanged!r}"
    )
    assert Task.CODE_GEN.value not in diff.added
    assert Task.CODE_GEN.value not in diff.changed
    assert Task.CODE_GEN.value not in diff.removed


def test_equal_snapshots_produce_only_unchanged() -> None:
    """Two equal snapshots → added={}, removed=set(), changed={}, unchanged=all.

    Kills impl that produces non-empty added or changed for identical inputs.
    """
    winners = {Task.CODE_GEN.value: "model-a", Task.SUMMARIZATION.value: "model-b"}
    before = TournamentSnapshot(winners=dict(winners), task_count=len(winners))
    after = TournamentSnapshot(winners=dict(winners), task_count=len(winners))

    diff = tournament_snapshot_diff(before, after)

    assert diff.added == {}, f"No tasks added between equal snapshots; got {diff.added!r}"
    assert diff.removed == set(), f"No tasks removed; got {diff.removed!r}"
    assert diff.changed == {}, f"No tasks changed; got {diff.changed!r}"
    assert diff.unchanged == set(winners.keys()), (
        f"All tasks must be unchanged; expected {set(winners.keys())!r}, got {diff.unchanged!r}"
    )
