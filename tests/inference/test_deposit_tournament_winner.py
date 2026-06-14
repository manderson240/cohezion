"""Item 151: deposit_tournament_winner — TDD red→green (2026-06-08).

``deposit_tournament_winner(result, *, store=None)`` closes the tournament→memory
loop: after ``model_tournament`` finds a winner, this deposits a country='inference'
neuron so future ticks can recall the preferred model without re-running the tournament.

Composes item-99 ``TournamentResult`` + item-15 deposit pattern (injectable store
kwarg; fail-soft in production).

Discriminating tests — each kills a plausible wrong implementation:

  1. No winner → no neuron deposited (store stays [])
     PRIMARY DISC.: kills "always deposit something"
  2. Clear winner → exactly one neuron, keyed task.value + "tournament-winner"
     Kills "deposit with wrong tags or wrong content"
  3. store=None → no exception raised (fail-soft)
     Kills impl that raises when production path can't write SurrealDB
  4. Neuron content == winner.model_id (correct identification of the winner)
     Kills "deposit content=task name or other field"
  5. Tags must include task.value AND "tournament-winner"
     Kills an impl that drops one of the two tags
"""

from __future__ import annotations

from cohezion.inference.model_tournament import TournamentResult
from cohezion.inference.registry import Lane, ModelEntry, Task, WeightQuant
from cohezion.inference.tournament_deposit import deposit_tournament_winner


def _entry(model_id: str) -> ModelEntry:
    return ModelEntry(
        model_id=model_id,
        lane=Lane.IGPU_ROCWMMA,
        endpoint="local://test",
        runtime_backend="test",
        weight_quant=WeightQuant.INT4,
        context_window=4096,
        task_affinity=frozenset({Task.CODE_GEN}),
        priority=15,
    )


def _result(winner: ModelEntry | None, task: Task = Task.CODE_GEN) -> TournamentResult:
    return TournamentResult(
        winner=winner,
        wins={} if winner is None else {winner.model_id: 1},
        margin=None if winner is None else 1,
        task=task,
        rationale="test",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_no_winner_deposits_nothing() -> None:
    """No winner (UNPROVEN) → store unchanged.

    PRIMARY DISCRIMINATOR: kills an impl that deposits a placeholder neuron
    even when the tournament produced no winner.
    """
    store: list[dict] = []
    deposit_tournament_winner(_result(winner=None), store=store)
    assert store == [], f"no winner must deposit nothing; store={store}"


def test_winner_deposits_one_neuron() -> None:
    """Clear winner → exactly one neuron deposited in the store."""
    store: list[dict] = []
    winner = _entry("Gemma-4-12B-it-qat-q4_0-GGUF")
    deposit_tournament_winner(_result(winner=winner), store=store)
    assert len(store) == 1, f"exactly one neuron must be deposited; store={store}"


def test_deposited_neuron_content_is_winner_model_id() -> None:
    """Neuron content is the winner's model_id (correct identification).

    Kills an impl that stores the task name or other field as content.
    """
    store: list[dict] = []
    winner = _entry("Gemma-4-12B-it-qat-q4_0-GGUF")
    deposit_tournament_winner(_result(winner=winner), store=store)
    assert store[0]["content"] == "Gemma-4-12B-it-qat-q4_0-GGUF", (
        f"neuron content must be winner.model_id; got {store[0]['content']}"
    )


def test_deposited_neuron_tags() -> None:
    """Tags must include task.value AND 'tournament-winner'.

    Kills an impl that drops one of the two required tags.
    """
    store: list[dict] = []
    winner = _entry("Gemma-4-12B-it-qat-q4_0-GGUF")
    deposit_tournament_winner(_result(winner=winner, task=Task.CODE_GEN), store=store)
    tags = store[0].get("tags", [])
    assert Task.CODE_GEN.value in tags, (
        f"task.value '{Task.CODE_GEN.value}' must be in tags; got {tags}"
    )
    assert "tournament-winner" in tags, f"'tournament-winner' must be in tags; got {tags}"


def test_store_none_does_not_raise() -> None:
    """store=None (production path) must not raise — fail-soft.

    Kills an impl that tries to write SurrealDB and crashes when it's unavailable.
    """
    winner = _entry("Gemma-4-12B-it-qat-q4_0-GGUF")
    try:
        deposit_tournament_winner(_result(winner=winner), store=None)
    except Exception as exc:
        raise AssertionError(f"deposit_tournament_winner must not raise; got {exc!r}") from exc
