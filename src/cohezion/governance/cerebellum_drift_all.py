"""Item 126: Multi-class cerebellum drift sweep — report-only (2026-06-08).

``cerebellum_drift_all(records, *, store)`` sweeps EVERY stabilized task_class in
the routing corpus and returns ALL whose current lane contradicts their stored
cerebellum neuron — not just the strongest one (which is all item-72
``cerebellum_drift`` sees).

A secondary drift (e.g. ``EMBED`` class quietly migrated from iGPU→CPU) is
invisible to item-72 because it only surfaces the single strongest pattern.  This
function groups records by task_class, applies the same per-class pattern + recall
comparison for EACH group, and collects every detected drift.

Composes item-72 ``cerebellum_drift`` (per-class logic) with a groupby over the
routing records.

Report-only — proposes the full stale-memory set; the update (re-deposit / refund)
stays gated.  Pure given an injected ``store``.
"""

from __future__ import annotations

from collections import defaultdict

from cohezion.governance.cerebellum_drift import cerebellum_drift


def cerebellum_drift_all(
    records: list[dict],
    *,
    store: list[dict] | None = None,
    min_samples: int = 5,
    min_consistency: float = 0.8,
) -> list[tuple[str, str, str]]:
    """Return every (task_class, old_lane, new_lane) where the current stable lane
    contradicts the stored cerebellum neuron for that task_class.

    Groups ``records`` by ``task_class``, then for each group calls the item-72
    single-class drift check.  A class with no stored neuron is NOVEL (not drift)
    and is excluded, consistent with item-72's semantics.

    Args:
        records:
            Routing-decision records, each a dict with at least ``task_class``,
            ``lane``, and ``fell_back`` keys (same shape as
            ``_detect_stable_routing_pattern``'s input).
        store:
            Injected cerebellum neuron store (list of neuron dicts).  ``None``
            falls through to the in-process default (empty list in tests).
        min_samples:
            Minimum decisions for a class to count as stabilized (default 5).
        min_consistency:
            Minimum fraction of non-fallback decisions on one lane to count as
            stable (default 0.8).

    Returns:
        Sorted list of ``(task_class, old_lane, new_lane)`` triples, one per
        drifted class.  Empty list when no drift detected.

    Pure — no graph access under test (``store`` is injected).  Report-only.
    """
    # Group records by task_class so each class gets its own stability check.
    by_class: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        tc = rec.get("task_class")
        if tc:
            by_class[str(tc)].append(rec)

    drifts: list[tuple[str, str, str]] = []
    for _task_class, class_records in by_class.items():
        drift = cerebellum_drift(
            class_records,
            store=store,
            min_samples=min_samples,
            min_consistency=min_consistency,
        )
        if drift is not None:
            drifts.append(drift)

    return sorted(drifts, key=lambda x: x[0])
