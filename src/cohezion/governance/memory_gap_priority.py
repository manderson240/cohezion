"""Item 129: Prioritized memory gaps — report-only (2026-06-08).

``memory_gap_priority(store, routing_records, *, task_classes)`` ranks gap
task_classes (those with NO procedural memory — item-75 ``memory_gaps``) by
how OFTEN the fleet routes them in ``routing_records``.

The most-routed UNREMEMBERED task is the highest-value memory to grow next:
filling it yields the greatest reduction in routing decisions without recall.

Composes:
  - Item 75 :func:`memory_gaps` — which task_classes lack procedural memory
    (per neuron country, across inference/skill/cerebellum).
  - Routing-record shape ``{task_class, lane, fell_back, ...}`` (same as
    ``_detect_stable_routing_pattern``'s input).

A COVERED task (has a stored neuron in any country) is excluded even if
routed often — coverage closes the gap regardless of routing frequency.
A gap that is never routed is also excluded — no traffic means no urgency.

Report-only — proposes priority; the deposit is the gated action.  Pure
given injected store + records.
"""

from __future__ import annotations

from collections import Counter

from cohezion.governance.neuron_quality import memory_gaps


def memory_gap_priority(
    store: list[dict],
    routing_records: list[dict],
    *,
    task_classes: list[str] | None = None,
) -> list[tuple[str, int]]:
    """Rank gap task_classes by routing frequency (highest priority first).

    Args:
        store:
            Injected neuron store (list of neuron dicts). Used by
            :func:`memory_gaps` to determine which task_classes are covered.
        routing_records:
            Routing-decision records, each with at least a ``task_class`` key.
        task_classes:
            The task-class universe to consider. ``None`` defaults to
            :class:`~cohezion.inference.registry.Task` names (same as
            :func:`memory_gaps`). Use explicit list in tests to avoid
            importing the live registry.

    Returns:
        ``[(task_class, route_count)]`` sorted descending by route_count.
        Only gap task_classes with ``route_count >= 1`` are included:
        - covered tasks are excluded (no gap to fill).
        - gaps with 0 routes are excluded (no urgency).

    Pure — no graph access (``store`` is injected).  Report-only.
    """
    # Resolve the gap set: cerebellum country only (the procedural-memory country).
    # The backlog item is specifically about the cerebellum gaps (the routing-memory
    # the bot uses to decide which engine to use); inference/skill gaps are separate concerns.
    gaps_by_country = memory_gaps(store, task_classes=task_classes)
    all_gaps: set[str] = gaps_by_country.get("cerebellum", set())

    if not all_gaps or not routing_records:
        return []

    # Count routing records for each task_class.
    routing_counts: Counter[str] = Counter()
    for rec in routing_records:
        tc = rec.get("task_class")
        if tc and str(tc) in all_gaps:
            routing_counts[str(tc)] += 1

    # Return gaps sorted by count descending; exclude 0-count gaps.
    return sorted(
        ((tc, count) for tc, count in routing_counts.items() if count > 0),
        key=lambda x: (-x[1], x[0]),
    )
