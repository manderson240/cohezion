"""Item 151: Tournament-winner neuron deposition — additive (2026-06-08).

Closes the tournament→memory loop: after ``model_tournament`` confirms a winner
for a ``Task``, ``deposit_tournament_winner`` deposits a ``country='inference'``
neuron so future loop ticks can recall the preferred model via
``loop_recall_context`` (item 108) without re-running the tournament.

Reuses the item-15 ``build_inference_neuron`` schema (same ``country='inference'``
region, same injectable ``store`` kwarg, same fail-soft pytest-skip guard).

Report-only in intent: proposes the winner neuron; never auto-swaps the live
registry.  Pure write path — no registry reads.
"""

from __future__ import annotations

from cohezion.inference.model_tournament import TournamentResult


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
