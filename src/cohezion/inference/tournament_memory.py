"""Item 151: Tournament-winner neuron deposition — report-only (2026-06-08).

``deposit_tournament_winner(result, *, store=None)`` closes the tournament→memory
loop: after ``model_tournament`` (item 99) confirms a winner for a ``Task``,
deposit a ``country='inference'`` neuron so future loop ticks can recall the
preferred model via ``loop_recall_context`` (item 108) without re-running the
tournament.

Neuron schema (mirrors item-15 ``build_inference_neuron`` / inference country):
  - ``name``:    ``tournament:<task.value>:winner``
  - ``content``: ``winner.model_id``
  - ``country``: ``"inference"``
  - ``tags``:    ``[task.value, "tournament-winner"]``

Injectable ``store`` kwarg (fail-soft like item 15):
  - ``store`` is a list → neuron is appended (test-safe, no real I/O).
  - ``store=None`` → fail-soft production path: never raises, never writes
    during pytest (same pytest-skip guard as ``deposit_inference_neuron``).

Report-only — proposes the neuron; the registry swap is a separate gated action.
Pure given injected store.
"""

from __future__ import annotations

from cohezion.inference.model_tournament import TournamentResult


def deposit_tournament_winner(
    result: TournamentResult,
    *,
    store: list[dict] | None = None,
) -> dict | None:
    """Deposit a neuron recording the tournament winner for ``result.task``.

    Args:
        result:
            The :class:`~cohezion.inference.model_tournament.TournamentResult`
            from ``model_tournament()``.  If ``result.winner is None``
            (UNPROVEN — no candidates) the function is a no-op; nothing is
            deposited and ``None`` is returned.
        store:
            Injected neuron store (a ``list[dict]``).  When provided, the
            neuron is appended and returned.  When ``None`` (production path),
            the function writes to ``KnowledgeBridge`` unless running under
            pytest — see the item-15 pytest-skip pattern.

    Returns:
        The deposited neuron dict, or ``None`` when no deposit was made.

    Report-only — proposes the neuron; never reads it back to auto-swap the
    registry.  Fail-soft: a write error never breaks the calling path.
    """
    if result.winner is None:
        return None  # UNPROVEN tournament → no memory to deposit

    neuron = {
        "name": f"tournament-winner:{result.task.value}",
        "content": result.winner.model_id,
        "country": "inference",
        "tags": [result.task.value, "tournament-winner"],
    }

    if store is not None:
        store.append(neuron)
        return neuron

    # Production path: fail-soft (never crashes the caller).
    try:
        import sys

        if "pytest" in sys.modules or "unittest" in sys.modules:
            return None  # never write real graph during tests
        from cohezion.governance.knowledge_bridge import deposit_inference_neuron_record

        deposit_inference_neuron_record(neuron)
        return neuron
    except Exception:
        return None
