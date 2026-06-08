"""Items 151 + 153 + 159: Tournament-winner neuron deposition & recall (2026-06-08).

Item 151 — ``deposit_tournament_winner``:
    Closes the tournament→memory write loop: after ``model_tournament`` confirms
    a winner for a ``Task``, deposits a ``country='inference'`` neuron so future
    loop ticks can recall the preferred model via ``loop_recall_context``
    (item 108) without re-running the tournament.

Item 153 — ``tournament_recall``:
    The read-side complement of item 151.  Given a ``Task`` and an injectable
    neuron store, returns the ``content`` (= ``model_id``) of the most recently
    appended neuron whose ``tags`` contain BOTH ``task.value`` AND
    ``"tournament-winner"``, or ``None`` if no such neuron exists.

Item 159 — ``tournament_recall_all``:
    Extends item 153 from single-task to all-tasks.  Scans the neuron store
    once and returns ``{task.value: model_id}`` for EVERY task that has at
    least one deposited winner (last-write-wins per task).  Tasks with no
    winner are absent from the dict (never present with a ``None`` value).

All three functions share the item-15 injectable-store pattern.  Pure given
injected store — no I/O, no SurrealDB write in pytest.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cohezion.inference.model_tournament import TournamentResult
from cohezion.inference.registry import Task


def deposit_tournament_winner(
    result: TournamentResult,
    *,
    store: list[dict] | None = None,
) -> dict | None:
    """Deposit a country='inference' neuron recording the tournament winner.

    If ``result.winner`` is ``None`` (UNPROVEN — no candidates or tie with no
    preference function) nothing is deposited and ``None`` is returned.

    Args:
        result:
            :class:`~cohezion.inference.model_tournament.TournamentResult` from
            :func:`~cohezion.inference.model_tournament.model_tournament`.
        store:
            Optional list to append the neuron dict to.  Provided in tests for
            round-trip inspection.  ``None`` → production path (SurrealDB via
            ``deposit_inference_neuron_record``); under ``pytest`` the production
            path is a no-op (fail-soft pytest-skip pattern, item 15).

    Returns:
        The deposited neuron dict, or ``None`` if nothing was deposited.

    Pure write path — no registry reads.  Fail-soft: never raises.
    """
    if result.winner is None:
        return None

    neuron = {
        "name": f"{result.task.value}:tournament-winner",
        "content": result.winner.model_id,
        "country": "inference",
        "tags": [result.task.value, "tournament-winner"],
        "embedding": [],
        "reward": 1.0,
    }

    if store is not None:
        store.append(neuron)
        return neuron

    # Production path — fail-soft: never break the loop if SurrealDB is unavailable.
    try:
        import sys

        if "pytest" in sys.modules or "unittest" in sys.modules:
            return None  # never touch the real graph during tests
        from cohezion.governance.knowledge_bridge import deposit_inference_neuron_record

        deposit_inference_neuron_record(neuron)
        return neuron
    except Exception:
        return None


def tournament_recall(
    task: Task,
    neurons: list[dict],
) -> str | None:
    """Recall the most recently deposited tournament-winner model_id for *task*.

    Scans *neurons* (the injectable neuron store) for the most recently appended
    entry whose ``tags`` list contains BOTH ``task.value`` AND
    ``"tournament-winner"``.  Returns ``neuron["content"]`` (the ``model_id``)
    of the last such match, or ``None`` if no winner has been deposited yet.

    "Most recently appended" is defined as the highest list-index — consistent
    with the append-only write path of :func:`deposit_tournament_winner`.

    Args:
        task:
            The :class:`~cohezion.inference.registry.Task` whose winner is being
            recalled.
        neurons:
            Iterable of neuron dicts (same shape as the item-15 injectable store).
            Only dicts whose ``"tags"`` list contains ``task.value`` AND
            ``"tournament-winner"`` are considered.

    Returns:
        The ``content`` (= ``model_id``) of the most recently deposited winner
        neuron for *task*, or ``None`` when no such neuron exists.

    Pure (no I/O, no SurrealDB).  Use an injected neuron list in tests.
    """
    winner: str | None = None
    for neuron in neurons:
        if not isinstance(neuron, dict):
            continue
        tags = neuron.get("tags") or []
        if task.value in tags and "tournament-winner" in tags:
            winner = str(neuron.get("content") or "")
    return winner if winner else None


def tournament_recall_all(neurons: list[dict]) -> dict[str, str]:
    """Recall the most recently deposited tournament-winner for every task that has one.

    Extends :func:`tournament_recall` from single-task to all-tasks.  Scans
    *neurons* once; for every task that has at least one deposited winner,
    records the most recently appended winner (last-write-wins per task).
    Tasks with no winner neuron are absent from the returned dict (never
    present with a ``None`` value).

    A neuron qualifies if its ``"tags"`` list contains BOTH
    ``"tournament-winner"`` AND a valid :class:`~cohezion.inference.registry.Task`
    value.  Neurons with only ``"tournament-winner"`` (no task.value tag) are
    excluded — they cannot be attributed to any task.

    Args:
        neurons:
            Iterable of neuron dicts (same shape as the item-15 injectable
            store).

    Returns:
        ``{task.value: model_id}`` for every task with at least one deposited
        winner.  Empty dict when no winners have been deposited.

    Pure (no I/O, no SurrealDB).  Use an injected neuron list in tests.
    """
    valid_task_values: frozenset[str] = frozenset(t.value for t in Task)
    result: dict[str, str] = {}
    for neuron in neurons:
        if not isinstance(neuron, dict):
            continue
        tags = neuron.get("tags") or []
        if "tournament-winner" not in tags:
            continue
        # Find the task.value tag — the one that is NOT "tournament-winner"
        # and IS a recognised Task enum value.  A neuron that carries only
        # "tournament-winner" (no task tag) is skipped.
        for tag in tags:
            if tag != "tournament-winner" and tag in valid_task_values:
                content = str(neuron.get("content") or "")
                if content:
                    result[tag] = content
                break
    return result


@dataclass(frozen=True)
class TournamentSnapshot:
    """Typed envelope around the output of :func:`tournament_recall_all` — item 162.

    Wraps the raw ``{task.value: model_id}`` dict from item 159 in a named,
    immutable dataclass so callers have a stable typed interface:

    Attributes:
        winners: ``{task.value: model_id}`` for every task with a deposited winner.
        task_count: Number of tasks with at least one winner (== ``len(winners)``).

    Methods:
        has_winner_for(task): Returns True if *task* has a deposited winner.
        from_neurons(neurons): Class-method constructor (delegates to
            :func:`tournament_recall_all`).

    Pure; no I/O.  Use :meth:`from_neurons` with an injected neuron list in tests.
    """

    winners: dict[str, str] = field(default_factory=dict)
    task_count: int = 0

    def has_winner_for(self, task: Task) -> bool:
        """Return ``True`` if *task* has a deposited tournament winner.

        Args:
            task: The :class:`~cohezion.inference.registry.Task` to check.

        Returns:
            ``True`` when ``task.value`` is a key in :attr:`winners`.
        """
        return task.value in self.winners

    @classmethod
    def from_neurons(cls, neurons: list[dict]) -> TournamentSnapshot:
        """Build a :class:`TournamentSnapshot` from an injectable neuron store.

        Delegates to :func:`tournament_recall_all` for winner discovery;
        computes :attr:`task_count` from the resulting dict.

        Args:
            neurons: Iterable of neuron dicts (same shape as the item-15
                injectable store).

        Returns:
            A new :class:`TournamentSnapshot` instance.
        """
        winners = tournament_recall_all(neurons)
        return cls(winners=winners, task_count=len(winners))
