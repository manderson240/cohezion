"""Item 112: Memory-pressure-aware storage GC — report-only eviction candidates.

``storage_gc_candidates`` proposes which storage records to evict/compact when the
store exceeds a budget — the STALEST + LOWEST-value records first.

**Non-destructive** (non-destructive-wiring policy): proposes candidates only, never
deletes.  The actual eviction is a separate, gated step.  A hash-chain-protected
record (audit trail integrity) is NEVER a candidate — only compaction of its payload
is permitted, not deletion.

Pure (injected records + budget; no live SurrealDB delete under pytest).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GCRecord:
    """A storage record eligible for GC evaluation (item 112).

    Attributes
    ----------
    id:
        Unique record identifier (e.g. SurrealDB record id string).
    age_days:
        How many days old the record is.  Older → higher eviction priority.
    size:
        Storage units consumed by this record (e.g. bytes, count, tokens).
    value_score:
        Quality / importance score in [0, 1].  Higher → keep preference.
        Supplied by local inference (semantic quality) or rule-based heuristic.
    hash_chain_protected:
        If ``True``, this record is part of the JourneyTracker hash-chain audit trail
        and may NEVER be evicted — only payload-compacted by a separate process.
        Default: ``False``.
    """

    id: str
    age_days: float
    size: int
    value_score: float
    hash_chain_protected: bool = False


def storage_gc_candidates(
    records: list[GCRecord],
    *,
    budget: int,
) -> list[GCRecord]:
    """Return eviction candidates when total storage exceeds budget (item 112). READ-ONLY.

    Selects the worst-priority records (lowest value, oldest age) to fill the overage
    gap.  Stops once the cumulative size of candidates meets or exceeds the overage;
    returns the full worst-priority ordered list up to that point.

    Args:
        records:
            All records in the storage layer.  Injected — no live DB call.
        budget:
            Maximum allowed total storage units.  When
            ``sum(r.size for r in records) <= budget``, returns ``[]``.

    Returns:
        List of :class:`GCRecord` sorted by eviction priority descending (worst record
        first — lowest ``value_score`` × recency).  Records are selected until their
        combined size covers the overage.  Returns ``[]`` when under budget or empty.
        Hash-chain-protected records are NEVER included.

    Eviction priority:
        Primary key: ``value_score`` ascending — low-value records evicted first.
        Secondary key: ``age_days`` descending — among equal-value records, older evicted first.
        Value dominates age: a high-value record is never chosen before a lower-value one
        regardless of how old it is.

    Pure (no deletes, no writes, no DB calls).
    """
    if not records:
        return []

    total_size = sum(r.size for r in records)
    overage = total_size - budget
    if overage <= 0:
        return []

    # Candidates are any unprotected record.
    candidates = [r for r in records if not r.hash_chain_protected]

    # Sort by eviction priority: lowest value first (primary), oldest age first (secondary).
    # Value is the PRIMARY sort key — a high-value record is never a candidate
    # even if it is very old (value dominates age).
    candidates.sort(key=lambda r: (r.value_score, -r.age_days))

    # Greedily select until cumulative size covers the overage.
    selected: list[GCRecord] = []
    covered = 0
    for rec in candidates:
        selected.append(rec)
        covered += rec.size
        if covered >= overage:
            break

    return selected
