"""Item 153: tournament_recall — TDD red→green (2026-06-08).

``tournament_recall(task, neurons)`` → ``str | None``:
the read-side complement of item-151 ``deposit_tournament_winner``.  Given a
``Task`` and a list of neuron dicts (injectable store), returns the ``content``
field (= ``model_id``) of the MOST RECENTLY APPENDED neuron whose ``tags``
contain BOTH ``task.value`` AND ``"tournament-winner"``, or ``None`` if no such
neuron exists.

Discriminating tests — each kills a plausible wrong implementation:

  1. Winner neuron present → returns model_id  (PRIMARY DISC.: kills always-None)
  2. No tournament-winner neuron → None         (kills impl that returns a default)
  3. Different-task winner present → None       (kills impl that ignores task filter)
  4. Multiple winners, last one wins            (kills impl that returns first/oldest)
  5. neuron missing "tournament-winner" tag → None  (kills impl that ignores tag filter)
"""

from __future__ import annotations

from cohezion.inference.registry import Task
from cohezion.inference.tournament_deposit import tournament_recall


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


def test_winner_neuron_returns_model_id() -> None:
    """Winner neuron present → returns model_id.

    PRIMARY DISCRIMINATOR: kills an impl that always returns None or that never
    reads back what was deposited.
    """
    neurons = [_neuron(Task.CODE_GEN, "Gemma-4-12B-it-qat-q4_0-GGUF")]
    result = tournament_recall(Task.CODE_GEN, neurons)
    assert result == "Gemma-4-12B-it-qat-q4_0-GGUF", f"expected model_id; got {result!r}"


def test_no_winner_neuron_returns_none() -> None:
    """No tournament-winner neuron in store → None.

    Kills an impl that returns a fallback model_id when no winner was deposited.
    """
    result = tournament_recall(Task.CODE_GEN, [])
    assert result is None, f"empty store must → None; got {result!r}"


def test_different_task_winner_returns_none() -> None:
    """Winner neuron for a DIFFERENT task → None for the queried task.

    Kills an impl that ignores task filtering and returns the first
    tournament-winner it finds regardless of task.value.
    """
    neurons = [_neuron(Task.GENERAL, "llama3.2-1b-FLM")]
    result = tournament_recall(Task.CODE_GEN, neurons)
    assert result is None, f"wrong-task winner must → None for CODE_GEN; got {result!r}"


def test_multiple_winners_returns_last() -> None:
    """Multiple tournament-winner neurons → the LAST one (most recent deposit).

    Kills an impl that returns the first match instead of the most recently
    appended one.  'Most recent' = highest list-index (last-write-wins,
    mirrors the append-only deposit path).
    """
    neurons = [
        _neuron(Task.CODE_GEN, "OlderModel-7B"),
        _neuron(Task.CODE_GEN, "NewerModel-12B"),
    ]
    result = tournament_recall(Task.CODE_GEN, neurons)
    assert result == "NewerModel-12B", f"last winner must be returned; got {result!r}"


def test_neuron_missing_tournament_winner_tag_returns_none() -> None:
    """Neuron with task.value tag but WITHOUT 'tournament-winner' tag → None.

    Kills an impl that filters only by task.value and ignores the
    'tournament-winner' tag requirement.
    """
    neurons = [_neuron(Task.CODE_GEN, "SomeModel-7B", winner_tag=False)]
    result = tournament_recall(Task.CODE_GEN, neurons)
    assert result is None, f"missing tournament-winner tag must → None; got {result!r}"
