"""Items 151 + 153: Tournament-winner neuron deposition & recall (2026-06-08).

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

Both functions share the item-15 injectable-store pattern.  Pure given injected
store — no I/O, no SurrealDB write in pytest.
"""

from __future__ import annotations

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
