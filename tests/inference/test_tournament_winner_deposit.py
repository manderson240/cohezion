"""Item 151: deposit_tournament_winner — TDD red→green (2026-06-08).

``deposit_tournament_winner(result, *, store=None)`` closes the
tournament→memory loop: after ``model_tournament`` confirms a winner, deposit
a ``country='inference'`` neuron so future loop ticks can recall the preferred
model without re-running the tournament.

Reuses the item-15 pattern (injectable ``store``, fail-soft production path).

Discriminating tests — each kills a plausible wrong implementation:

  1. No winner (result.winner=None) → no neuron deposited      (PRIMARY DISC.)
     Kills "always deposit something regardless of winner"
  2. Clear winner → exactly one neuron in store                (kills "deposit nothing")
  3. Neuron has task.value + 'tournament-winner' identity key  (kills "wrong name/tags")
  4. store=None (production path) → no exception raised        (kills "crashes on None store")
  5. Neuron content is winner.model_id                         (kills "content = task name")
"""

from __future__ import annotations

from cohezion.inference.model_tournament import TournamentResult
from cohezion.inference.registry import Lane, ModelEntry, Task, WeightQuant
from cohezion.inference.tournament_memory import deposit_tournament_winner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entry(model_id: str, task: Task = Task.CODE_GEN) -> ModelEntry:
    return ModelEntry(
        model_id=model_id,
        lane=Lane.IGPU_ROCWMMA,
        endpoint="http://localhost:0",
        runtime_backend="test",
        weight_quant=WeightQuant.INT4,
        context_window=4096,
        task_affinity=frozenset({task}),
        priority=10,
    )


def _result_no_winner(task: Task = Task.CODE_GEN) -> TournamentResult:
    return TournamentResult(winner=None, wins={}, margin=None, task=task, rationale="UNPROVEN")


def _result_with_winner(
    model_id: str = "test-model", task: Task = Task.CODE_GEN
) -> TournamentResult:
    entry = _entry(model_id, task)
    return TournamentResult(
        winner=entry,
        wins={model_id: 2},
        margin=2,
        task=task,
        rationale=f"preferred {model_id}",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_no_winner_deposits_nothing() -> None:
    """result.winner=None → no neuron deposited, store stays empty.

    PRIMARY DISCRIMINATOR: kills an impl that always deposits a neuron
    regardless of whether a winner exists.
    """
    store: list[dict] = []
    deposit_tournament_winner(_result_no_winner(), store=store)
    assert store == [], f"no winner → store must stay empty; got {store}"


def test_clear_winner_deposits_one_neuron() -> None:
    """Clear winner → exactly one neuron appended to store.

    Kills an impl that never deposits anything.
    """
    store: list[dict] = []
    result = deposit_tournament_winner(_result_with_winner("best-model"), store=store)
    assert len(store) == 1, f"exactly one neuron expected; got {store}"
    assert result is not None, "must return the deposited neuron"


def test_neuron_has_tournament_winner_identity() -> None:
    """The neuron name/tags encode task.value + 'tournament-winner' for future recall.

    Kills an impl that stores the neuron with a different key, making recall impossible.
    """
    store: list[dict] = []
    deposit_tournament_winner(_result_with_winner("model-x", Task.CODE_GEN), store=store)
    neuron = store[0]
    # Name must identify the task and the 'tournament-winner' context.
    assert "tournament-winner" in str(neuron.get("name", "")), (
        f"name must contain 'tournament-winner'; got {neuron.get('name')}"
    )
    assert Task.CODE_GEN.value in str(neuron.get("name", "")), (
        f"name must contain task value; got {neuron.get('name')}"
    )
    tags = neuron.get("tags", [])
    assert "tournament-winner" in tags, f"'tournament-winner' must be in tags; got {tags}"
    assert Task.CODE_GEN.value in tags, f"task value must be in tags; got {tags}"


def test_store_none_does_not_raise() -> None:
    """store=None (production path) → fail-soft, no exception.

    Mirrors the item-15 pytest-skip pattern: never crashes the routing path
    even if the production write fails.
    """
    result = _result_with_winner("prod-model")
    # Must NOT raise, even without an injected store.
    deposit_tournament_winner(result, store=None)


def test_neuron_content_is_winner_model_id() -> None:
    """The neuron content carries the winner.model_id (not the task name).

    Kills an impl that stores the task name as content, making recall look
    up the wrong model.
    """
    store: list[dict] = []
    deposit_tournament_winner(_result_with_winner("winner-model-42"), store=store)
    neuron = store[0]
    assert "winner-model-42" in str(neuron.get("content", "")), (
        f"content must include winner.model_id; got {neuron.get('content')}"
    )
