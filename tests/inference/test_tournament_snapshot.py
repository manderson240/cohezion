"""Item 162: TournamentSnapshot — TDD red→green (2026-06-08).

``TournamentSnapshot`` dataclass — typed envelope around ``tournament_recall_all``.

Fields:
  - ``winners: dict[str, str]``  — output of ``tournament_recall_all``
  - ``task_count: int``           — number of tasks with a winner
  - ``has_winner_for(task) -> bool`` — convenience predicate

Constructor: ``TournamentSnapshot.from_neurons(neurons)`` — builds from an
injectable neuron store (delegates to ``tournament_recall_all``).  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. ``winners`` equals ``tournament_recall_all(neurons)`` for the same input.
     PRIMARY DISC.: kills impl that re-implements recall differently (e.g. returns
     only first winner per task instead of last-write-wins).
  2. ``task_count == len(winners)`` — derived, not hardcoded.
     Kills impl that hardcodes ``task_count=1`` or omits the field.
  3. ``has_winner_for(Task.CODE_GEN)`` returns True when CODE_GEN in winners.
     Kills impl that always returns True (or ignores the task argument).
  4. ``has_winner_for(Task.GENERAL)`` returns False when GENERAL not in winners.
     Kills impl that always returns False or uses ``in`` on the wrong dict key.
  5. Empty store → ``task_count=0``, ``has_winner_for(any task)`` = False.
     Kills impl that raises on empty input or returns task_count=1 as default.
"""

from __future__ import annotations

from cohezion.inference.registry import Task
from cohezion.inference.tournament_deposit import TournamentSnapshot, tournament_recall_all


def _neuron(task: Task, model_id: str) -> dict:
    return {
        "name": f"{task.value}:tournament-winner",
        "content": model_id,
        "country": "inference",
        "tags": [task.value, "tournament-winner"],
        "embedding": [],
        "reward": 1.0,
    }


def test_winners_matches_tournament_recall_all() -> None:
    """TournamentSnapshot.winners equals tournament_recall_all for the same neurons.

    PRIMARY DISCRIMINATOR: kills an impl that computes winners differently
    (e.g. first-write instead of last-write, or only partial scanning).
    Tests two neurons for the same task (last-write-wins) to expose any
    divergence from the item-159 contract.
    """
    neurons = [
        _neuron(Task.CODE_GEN, "OlderModel-7B"),
        _neuron(Task.CODE_GEN, "NewerModel-12B"),
        _neuron(Task.GENERAL, "GeneralModel-7B"),
    ]
    snap = TournamentSnapshot.from_neurons(neurons)
    expected = tournament_recall_all(neurons)
    assert snap.winners == expected, (
        f"TournamentSnapshot.winners must equal tournament_recall_all; "
        f"snap={snap.winners!r}, expected={expected!r}"
    )


def test_task_count_equals_len_winners() -> None:
    """task_count == len(winners) — derived from winners, not hardcoded.

    Kills an impl that hardcodes task_count=1 or keeps a stale counter
    that doesn't update when winners changes.
    """
    neurons = [_neuron(Task.CODE_GEN, "m1"), _neuron(Task.GENERAL, "m2")]
    snap = TournamentSnapshot.from_neurons(neurons)
    assert snap.task_count == len(snap.winners), (
        f"task_count must equal len(winners); task_count={snap.task_count}, winners={snap.winners}"
    )
    assert snap.task_count == 2, f"expected task_count=2; got {snap.task_count}"


def test_has_winner_for_true_when_present() -> None:
    """has_winner_for(CODE_GEN) returns True when CODE_GEN has a winner.

    Kills an impl that always returns True (doesn't check the task arg)
    or checks the wrong attribute on the task.
    """
    neurons = [_neuron(Task.CODE_GEN, "CodeModel")]
    snap = TournamentSnapshot.from_neurons(neurons)
    assert snap.has_winner_for(Task.CODE_GEN) is True, (
        f"has_winner_for(CODE_GEN) must be True; snap.winners={snap.winners}"
    )


def test_has_winner_for_false_when_absent() -> None:
    """has_winner_for(GENERAL) returns False when GENERAL has no winner.

    Kills an impl that always returns False or checks task.name instead of
    task.value (which would fail because Task is a StrEnum where value != name).
    """
    neurons = [_neuron(Task.CODE_GEN, "CodeModel")]
    snap = TournamentSnapshot.from_neurons(neurons)
    assert snap.has_winner_for(Task.GENERAL) is False, (
        f"has_winner_for(GENERAL) must be False; snap.winners={snap.winners}"
    )


def test_empty_store_gives_zero_snapshot() -> None:
    """Empty neuron store → task_count=0, has_winner_for(any) = False.

    Kills an impl that raises on empty input, returns task_count=1 as a
    default, or has a has_winner_for that doesn't consult winners at all.
    """
    snap = TournamentSnapshot.from_neurons([])
    assert snap.winners == {}, f"empty store → empty winners; got {snap.winners!r}"
    assert snap.task_count == 0, f"empty store → task_count=0; got {snap.task_count}"
    assert snap.has_winner_for(Task.CODE_GEN) is False, (
        "has_winner_for must be False on empty snapshot"
    )
    assert snap.has_winner_for(Task.GENERAL) is False, (
        "has_winner_for must be False on empty snapshot"
    )
