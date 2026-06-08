"""Cerebellum procedural-memory drift detector (backlog item 72, 2026-06-07).

The next concern after item-51 dedup: a STORED cerebellum neuron (procedural routing memory —
"this task_class reliably routes to this lane") can go STALE when the fleet's optimal lane for
that task_class changes (a model swap, a new tier, a thermal shift). Item 51 stops DUPLICATE
deposits; this flags a CONTRADICTED one.

`cerebellum_drift(records, *, store)` composes item-24 `_detect_stable_routing_pattern` (the
current stabilized lane from the routing corpus) + item-29 `recall_neurons` (the stored
cerebellum neuron's lane). When they disagree → `(task_class, old_lane, new_lane)`. Report-only:
it FLAGS stale procedural memory; the actual memory UPDATE (re-deposit / refund the old neuron)
is a separate gated action. Pure given an injected ``store`` — no real graph read under pytest
(inherited from `recall_neurons`).

Lives in a separate module (not `knowledge_bridge`, already >500 LOC — the item-52 precedent).
"""

from __future__ import annotations

from cohezion.governance.knowledge_bridge import (
    _detect_stable_routing_pattern,
    recall_neurons,
)


def _stored_lane(neuron: dict) -> str | None:
    """The lane a cerebellum neuron records: from its name ``cerebellum:{tc}->{lane}`` or tags[3]."""
    name = str(neuron.get("name", ""))
    if "->" in name:
        return name.rsplit("->", 1)[1].strip()
    tags = neuron.get("tags") or []
    return str(tags[3]) if len(tags) >= 4 else None


def cerebellum_drift(
    records: list[dict],
    *,
    store: list[dict] | None = None,
    min_samples: int = 5,
    min_consistency: float = 0.8,
) -> tuple[str, str, str] | None:
    """Detect when the current stable lane differs from the stored cerebellum lane (item 72).

    Returns ``(task_class, old_lane, new_lane)`` when the routing corpus has stabilized on a lane
    that DIFFERS from the stored cerebellum neuron's lane for that task_class — else ``None``:
      - no current stable pattern (noise / fallback-heavy) → None,
      - no stored cerebellum neuron for the task_class → None (NOVEL stabilization, not drift),
      - stored lane == current lane → None (procedural memory still correct).
    Report-only, pure given ``store``. Flags stale memory; does not update it (that is gated).
    """
    pattern = _detect_stable_routing_pattern(
        records, min_samples=min_samples, min_consistency=min_consistency
    )
    if pattern is None:
        return None  # no stabilized pattern → nothing to compare
    task_class, new_lane = pattern[0], pattern[1]
    recalled = recall_neurons("cerebellum", task_class, store=store)
    if not recalled:
        return None  # novel stabilization, not drift
    old_lane = _stored_lane(recalled[0])
    if old_lane is None or old_lane == new_lane:
        return None  # unparseable or unchanged → no drift
    return (task_class, old_lane, new_lane)


def cerebellum_drift_all(
    records: list[dict],
    *,
    store: list[dict] | None = None,
    min_samples: int = 5,
    min_consistency: float = 0.8,
) -> list[tuple[str, str, str]]:
    """Multi-class cerebellum drift sweep (item 126) — composes per-class :func:`cerebellum_drift`.

    item-72 :func:`cerebellum_drift` surfaces only the SINGLE strongest stabilized pattern, so a
    drift in a secondary task_class is invisible to it. A real fleet stabilizes MANY classes; this
    groups ``records`` by task_class and runs the per-class drift check on each, returning EVERY
    stabilized task_class whose current lane contradicts its stored cerebellum neuron (a class with
    no stored neuron is NOVEL, not drift, and excluded). Returns ``(task_class, old_lane, new_lane)``
    tuples sorted by task_class. Report-only, pure given ``store``.
    """
    by_class: dict[str, list[dict]] = {}
    for rec in records:
        task_class = rec.get("task_class")
        if task_class is not None:
            by_class.setdefault(str(task_class), []).append(rec)

    drifts: list[tuple[str, str, str]] = []
    for class_records in by_class.values():
        drift = cerebellum_drift(
            class_records,
            store=store,
            min_samples=min_samples,
            min_consistency=min_consistency,
        )
        if drift is not None:
            drifts.append(drift)
    return sorted(drifts, key=lambda d: d[0])
