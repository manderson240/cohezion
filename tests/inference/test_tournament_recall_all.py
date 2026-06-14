"""Item 159: tournament_recall_all — TDD red→green (2026-06-08).

``tournament_recall_all(neurons)`` → ``dict[str, str]``:
extends item-153 ``tournament_recall`` from single-task to all-tasks.  Given a
neuron store (injectable list), returns ``{task.value: model_id}`` for EVERY
task that has at least one deposited tournament-winner neuron.  Tasks with no
winner are absent (not present with a None value).  Pure read-only; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. Two different tasks each with a winner → dict with 2 entries
     PRIMARY DISC.: kills impl that returns only one task's winner.
  2. Empty store → empty dict.
     Kills impl that raises KeyError or returns a dict with None values.
  3. Winner for task A but not task B → only task A in dict.
     Kills impl that includes tasks with no deposited winner.
  4. Multiple neurons for the same task → most-recent wins (last-write).
     Kills impl that returns oldest or first match.
  5. Neuron with 'tournament-winner' tag but no task.value tag → excluded.
     Kills impl that ignores task filtering and maps all tournament-winners.
"""

from __future__ import annotations

from cohezion.inference.registry import Task
from cohezion.inference.tournament_deposit import tournament_recall_all


def _neuron(task: Task, model_id: str, *, winner_tag: bool = True) -> dict:
    tags = [task.value]
    if winner_tag:
        tags.append("tournament-winner")
    return {
        "name": f"{task.value}:tournament-winner",
        "content": model_id,
        "country": "inference",
        "tags": tags,
        "embedding": [],
        "reward": 1.0,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_two_tasks_both_recalled() -> None:
    """Two tasks with winners → dict with exactly 2 entries.

    PRIMARY DISCRIMINATOR: kills an impl that only returns the first winner
    found or stops scanning after the first task.
    """
    neurons = [
        _neuron(Task.CODE_GEN, "CodeModel-12B"),
        _neuron(Task.GENERAL, "GeneralModel-7B"),
    ]
    result = tournament_recall_all(neurons)
    assert result.get(Task.CODE_GEN.value) == "CodeModel-12B", (
        f"CODE_GEN winner should be recalled; got {result}"
    )
    assert result.get(Task.GENERAL.value) == "GeneralModel-7B", (
        f"GENERAL winner should be recalled; got {result}"
    )
    assert len(result) == 2, f"expected 2 entries; got {result}"


def test_empty_store_returns_empty_dict() -> None:
    """Empty neuron store → empty dict (no error).

    Kills an impl that raises on empty input or returns a dict with None values
    for task entries that have no winner.
    """
    result = tournament_recall_all([])
    assert result == {}, f"empty store must → empty dict; got {result!r}"


def test_only_winner_tasks_appear() -> None:
    """Only task A has a winner; task B has no neuron → only task A in dict.

    Kills an impl that includes ALL tasks as keys (even those without a winner),
    which would return e.g. {task_b_value: None}.
    """
    neurons = [_neuron(Task.CODE_GEN, "CodeModel-12B")]
    result = tournament_recall_all(neurons)
    assert Task.CODE_GEN.value in result, f"CODE_GEN must be in result; got {result}"
    assert Task.GENERAL.value not in result, (
        f"GENERAL (no winner) must NOT be in result; got {result}"
    )


def test_multiple_neurons_same_task_last_wins() -> None:
    """Multiple winner neurons for the same task → most recent (last-write) wins.

    Kills an impl that returns the first match instead of the last-appended one.
    Consistent with item-153 last-write-wins semantics.
    """
    neurons = [
        _neuron(Task.CODE_GEN, "OlderModel-7B"),
        _neuron(Task.CODE_GEN, "NewerModel-12B"),
    ]
    result = tournament_recall_all(neurons)
    assert result.get(Task.CODE_GEN.value) == "NewerModel-12B", (
        f"last winner must win; got {result}"
    )


def test_neuron_without_task_value_tag_excluded() -> None:
    """Neuron with 'tournament-winner' tag but missing the task.value tag → excluded.

    Kills an impl that includes any neuron with 'tournament-winner' in tags
    regardless of whether it also has the task.value tag.
    The test creates a neuron with only 'tournament-winner' (no task.value).
    """
    # A neuron with ONLY the 'tournament-winner' tag, no task.value tag.
    orphan_neuron = {
        "name": "orphan-winner",
        "content": "OrphanModel-5B",
        "country": "inference",
        "tags": ["tournament-winner"],  # missing task.value
        "embedding": [],
    }
    result = tournament_recall_all([orphan_neuron])
    assert result == {}, f"neuron without task.value tag must be excluded; got {result!r}"
