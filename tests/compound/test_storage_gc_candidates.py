"""Item 112: storage_gc_candidates(records, *, budget, score_fn) — TDD red→green.

Returns the lowest-value + stalest records totalling the overage when over budget.
Never deletes (report-only candidates). Hash-chain-protected records excluded.

Discriminating tests — each kills a plausible wrong implementation:
  - over-budget → returns candidates that total the overage     → test_over_budget_returns_candidates (MAIN DISC.)
  - under-budget → empty (no unnecessary GC)                   → test_under_budget_empty
  - high-value recent record NEVER a candidate                  → test_high_value_not_candidate
  - hash-chain-protected record excluded                        → test_hash_chain_excluded
  - empty records → []                                         → test_empty_records_empty
  - candidates sorted worst-first (lowest value * recency)     → test_candidates_ordered_worst_first
  - over-budget by exactly 1 unit → at least 1 candidate       → test_exact_overage_one_candidate
"""

from __future__ import annotations

from cohezion.compound.storage_gc import GCRecord, storage_gc_candidates

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BUDGET = 100  # storage unit budget (e.g. record count)


def _rec(
    id_: str,
    age_days: float,
    size: int,
    value: float,
    hash_chain_protected: bool = False,
) -> GCRecord:
    return GCRecord(
        id=id_,
        age_days=age_days,
        size=size,
        value_score=value,
        hash_chain_protected=hash_chain_protected,
    )


# ---------------------------------------------------------------------------
# Core correctness
# ---------------------------------------------------------------------------


def test_over_budget_returns_candidates() -> None:
    """Over-budget store → returns records with combined size >= overage.

    PRIMARY DISCRIMINATOR: kills an impl that always returns [] or ignores budget.
    """
    # Total size = 120, budget = 100 → overage = 20
    records = [
        _rec("a", age_days=30.0, size=60, value=0.1),  # old, low value → top candidate
        _rec("b", age_days=5.0, size=60, value=0.9),  # recent, high value → keep
    ]
    candidates = storage_gc_candidates(records, budget=BUDGET)
    assert len(candidates) >= 1, "Over budget must return candidates"
    cand_ids = [c.id for c in candidates]
    assert "a" in cand_ids, f"Low-value old record 'a' must be a candidate; got {cand_ids}"


def test_under_budget_empty() -> None:
    """Under-budget store → empty candidate list (nothing to GC).

    Kills an impl that always returns the lowest-value records regardless of budget.
    """
    records = [
        _rec("a", age_days=30.0, size=30, value=0.1),
        _rec("b", age_days=5.0, size=30, value=0.9),
    ]  # total = 60 < budget = 100
    candidates = storage_gc_candidates(records, budget=BUDGET)
    assert candidates == [], f"Under budget → no candidates; got {candidates}"


def test_high_value_not_candidate() -> None:
    """A high-value recent record is NEVER a candidate even if store is over budget.

    Kills an impl that blindly picks the smallest record regardless of value.
    value dominates: a high-value record must not appear in candidates.
    """
    records = [
        _rec("low_val", age_days=1.0, size=80, value=0.05),  # low value → candidate
        _rec("high_val", age_days=100.0, size=80, value=0.95),  # high value → keep
    ]  # total = 160 > 100
    candidates = storage_gc_candidates(records, budget=BUDGET)
    cand_ids = [c.id for c in candidates]
    assert "high_val" not in cand_ids, f"high-value record must NOT be a candidate; got {cand_ids}"
    assert "low_val" in cand_ids, f"low-value record must be a candidate; got {cand_ids}"


def test_hash_chain_excluded() -> None:
    """A hash-chain-protected record is NEVER a candidate (audit integrity).

    Kills an impl that ignores the hash_chain_protected flag.
    The protected record has the lowest value, but must never appear.
    """
    records = [
        _rec("protected", age_days=365.0, size=80, value=0.0, hash_chain_protected=True),
        _rec("normal", age_days=1.0, size=80, value=0.1, hash_chain_protected=False),
    ]  # total = 160 > 100
    candidates = storage_gc_candidates(records, budget=BUDGET)
    cand_ids = [c.id for c in candidates]
    assert "protected" not in cand_ids, (
        f"hash-chain-protected record must NEVER be a candidate; got {cand_ids}"
    )


def test_empty_records_empty() -> None:
    """Empty records → empty candidates. No crash."""
    candidates = storage_gc_candidates([], budget=BUDGET)
    assert candidates == []


def test_candidates_ordered_worst_first() -> None:
    """Candidates are ordered worst-first (lowest value × recency priority).

    Kills an impl that returns candidates in insertion order.
    The most evictable (lowest value + oldest) must rank first.
    """
    records = [
        _rec("worst", age_days=100.0, size=40, value=0.1),  # worst: old + low value
        _rec("medium", age_days=50.0, size=40, value=0.3),  # medium
        _rec("best", age_days=10.0, size=40, value=0.8),  # best: recent + high value
    ]  # total = 120 > 100; need to evict at least 20
    candidates = storage_gc_candidates(records, budget=BUDGET)
    assert len(candidates) >= 1
    assert candidates[0].id == "worst", (
        f"Worst record must rank first in candidates; got {[c.id for c in candidates]}"
    )


def test_exact_overage_one_candidate() -> None:
    """Exactly at budget+1 → at least 1 candidate returned (boundary not missed)."""
    records = [
        _rec("old_low", age_days=50.0, size=101, value=0.1),
    ]  # 101 > 100
    candidates = storage_gc_candidates(records, budget=BUDGET)
    assert len(candidates) >= 1, "Overage of 1 unit must still trigger GC candidates"
