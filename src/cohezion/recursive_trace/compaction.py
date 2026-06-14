"""Item 120: Recursive-trace latent densification — compaction measurement (2026-06-08).

``trace_compaction_ratio(records)`` measures how well the recursive trace store
DENSIFIES raw failure→strategy observations into reusable strategy patterns.

The "floppy-disk analogy" (user lesson 2026-06-06):
  A floppy disk stores raw sectors that can be defragmented — densified — so that
  fewer physical locations serve more logical reads.  The trace store is analogous:
  ideally many distinct failure_class events collapse to FEW reusable strategies
  (high compaction_ratio), rather than accumulating one unique strategy per event
  (ratio ≈ 1.0 = no densification = the un-evolved floppy).

This operationalises the ``TraceMemory`` seam (core.py:46) WITHOUT fabricating
Stage-2 latent retrieval (``LatentStateTracker.enabled=False`` — stays gated).
Report-only, additive, pure.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompactionReport:
    """Compaction density report for the recursive trace store (item 120).

    Attributes
    ----------
    n_records:
        Total number of (failure_class, strategy) records in the store.
    n_distinct_strategies:
        Number of UNIQUE strategy values across all records.
    compaction_ratio:
        ``n_records / n_distinct_strategies``.  A ratio of 1.0 means no
        densification (every record is a unique strategy); a ratio of 6.0
        means 6 raw records compressed into 1 strategy — high densification.
        0.0 when the store is empty (avoids ZeroDivisionError, signals "unknown").
    """

    n_records: int
    n_distinct_strategies: int
    compaction_ratio: float


def trace_compaction_ratio(
    records: list[tuple[str, str]],
) -> CompactionReport:
    """Measure storage-density evolution of the recursive trace store (item 120). Pure.

    Counts how many raw ``(failure_class, strategy)`` records exist versus how many
    DISTINCT strategies serve them — the higher the ratio, the more the loop has
    learned to REUSE strategies across failure classes instead of inventing a new one
    each time.

    Args:
        records:
            List of ``(failure_class, strategy)`` pairs from the trace store.
            The ``failure_class`` is the observed symptom (e.g. ``"latency"``);
            ``strategy`` is the approach used to resolve it (e.g. ``"tier_downgrade"``).
            Compaction counts unique ``strategy`` values only — duplicate
            strategies across different failure classes indicate densification.

    Returns:
        A :class:`CompactionReport` with:
          - ``n_records``: total record count.
          - ``n_distinct_strategies``: number of distinct strategy strings.
          - ``compaction_ratio``: ``n_records / n_distinct_strategies``,
            or ``0.0`` when ``records`` is empty.

    Pure — operates on an injected list; no SurrealDB, no embedding store,
    no Stage-2 latent retrieval (``LatentStateTracker.enabled=False`` remains).
    Report-only — measures density, never deletes or modifies the store.
    """
    if not records:
        return CompactionReport(n_records=0, n_distinct_strategies=0, compaction_ratio=0.0)

    n_records = len(records)
    # Count distinct strategy values (not failure_class — see docstring).
    distinct_strategies = {strategy for _failure_class, strategy in records}
    n_distinct = len(distinct_strategies)

    return CompactionReport(
        n_records=n_records,
        n_distinct_strategies=n_distinct,
        compaction_ratio=n_records / n_distinct,
    )
