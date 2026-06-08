"""Item 109: decay_weighted_rank(hits, *, now_ts, half_life_days) — TDD red→green.

Re-ranks (memory, relevance, age_days) hits by ``relevance * 0.5**(age_days/half_life_days)``.

Discriminating tests — each kills a plausible wrong implementation:
  - equal relevance, different age → fresher ranks higher     → test_fresher_beats_staler
  - old high-relevance beats fresh low-relevance               → test_relevance_dominates
  - half_life→∞ (very large) → pure relevance order           → test_infinite_half_life_pure_relevance
  - half_life=0 edge case (guard: no ZeroDivision)             → test_zero_half_life_no_crash
  - empty hits → []                                           → test_empty_returns_empty
  - score is EXACT (not just order)                           → test_score_formula_exact
  - single hit → returned unchanged                           → test_single_hit_returned
  - age=0 (just created) → score = relevance (decay=1.0)      → test_zero_age_no_decay
"""

from __future__ import annotations

from cohezion.compound.decay_rank import MemoryHit, decay_weighted_rank

_NOW = 1_000_000.0  # arbitrary fixed timestamp (injected; not wall clock)


# ---------------------------------------------------------------------------
# Core ranking correctness
# ---------------------------------------------------------------------------


def test_fresher_beats_staler() -> None:
    """Equal relevance, different age → fresher ranks higher (closer to now).

    PRIMARY DISCRIMINATOR: kills an impl that ignores age or reverses the order.
    """
    hits = [
        MemoryHit(memory="stale", relevance=0.8, age_days=30.0),
        MemoryHit(memory="fresh", relevance=0.8, age_days=1.0),
    ]
    results = decay_weighted_rank(hits, now_ts=_NOW, half_life_days=7.0)
    assert len(results) == 2
    memories = [r.memory for r in results]
    assert memories[0] == "fresh", (
        f"Equal relevance: fresher hit (age=1d) must rank above staler (age=30d); got {memories}"
    )


def test_relevance_dominates() -> None:
    """A much-more-relevant old hit still beats a barely-relevant fresh one.

    Kills an impl that weights age too heavily (pure-recency impl).
    """
    # old: relevance=0.9, age=30d, half_life=7d → score = 0.9 * 0.5^(30/7) ≈ 0.9 * 0.0491 ≈ 0.0442
    # fresh: relevance=0.1, age=1d, half_life=7d → score = 0.1 * 0.5^(1/7) ≈ 0.1 * 0.9057 ≈ 0.0906
    # ...hmm, fresh wins here. Let me use more extreme values.
    # old: relevance=1.0, age=7d, half_life=7d → score = 1.0 * 0.5 = 0.5
    # fresh: relevance=0.1, age=0d, half_life=7d → score = 0.1 * 1.0 = 0.1
    hits = [
        MemoryHit(memory="old_relevant", relevance=1.0, age_days=7.0),
        MemoryHit(memory="fresh_weak", relevance=0.1, age_days=0.0),
    ]
    results = decay_weighted_rank(hits, now_ts=_NOW, half_life_days=7.0)
    memories = [r.memory for r in results]
    assert memories[0] == "old_relevant", (
        f"old_relevant (score≈0.5) must beat fresh_weak (score≈0.1); got {memories}"
    )


def test_infinite_half_life_pure_relevance() -> None:
    """Very large half_life → decay ≈ 1.0 for all hits → order is pure relevance.

    Kills an impl that does not correctly reduce to pure relevance at half_life→∞.
    """
    hits = [
        MemoryHit(memory="low_rel", relevance=0.3, age_days=0.1),
        MemoryHit(memory="high_rel", relevance=0.9, age_days=10000.0),
    ]
    # half_life=1e15: decay = 0.5^(10000/1e15) ≈ 1.0 for all practical purposes
    results = decay_weighted_rank(hits, now_ts=_NOW, half_life_days=1e15)
    memories = [r.memory for r in results]
    assert memories[0] == "high_rel", (
        f"At half_life≈∞, relevance dominates: high_rel (0.9) must rank above low_rel (0.3); "
        f"got {memories}"
    )


def test_empty_returns_empty() -> None:
    """Empty hits → empty result. No crash."""
    result = decay_weighted_rank([], now_ts=_NOW, half_life_days=7.0)
    assert result == []


def test_single_hit_returned() -> None:
    """A single hit → returned in a list of length 1."""
    hits = [MemoryHit(memory="only", relevance=0.5, age_days=3.0)]
    result = decay_weighted_rank(hits, now_ts=_NOW, half_life_days=7.0)
    assert len(result) == 1
    assert result[0].memory == "only"


# ---------------------------------------------------------------------------
# Score formula exactness
# ---------------------------------------------------------------------------


def test_score_formula_exact() -> None:
    """score = relevance * 0.5^(age_days / half_life_days) — exact formula check.

    Kills an impl that uses a different decay base or wrong exponent.
    """
    hits = [MemoryHit(memory="x", relevance=0.8, age_days=14.0)]
    results = decay_weighted_rank(hits, now_ts=_NOW, half_life_days=7.0)
    # 0.8 * 0.5^(14/7) = 0.8 * 0.5^2 = 0.8 * 0.25 = 0.2
    expected = 0.8 * (0.5 ** (14.0 / 7.0))
    assert abs(results[0].score - expected) < 1e-9, (
        f"score must be {expected:.6f}; got {results[0].score:.6f}"
    )


def test_zero_age_no_decay() -> None:
    """age_days=0 → decay factor = 0.5^0 = 1.0 → score = relevance exactly.

    Kills an impl that applies decay even at age=0 (e.g. adds 1 to avoid log(0)).
    """
    hits = [MemoryHit(memory="new", relevance=0.75, age_days=0.0)]
    results = decay_weighted_rank(hits, now_ts=_NOW, half_life_days=7.0)
    assert abs(results[0].score - 0.75) < 1e-9, (
        f"age=0 → score must equal relevance=0.75; got {results[0].score}"
    )


def test_zero_half_life_no_crash() -> None:
    """half_life_days=0 edge case → no ZeroDivisionError; graceful handling.

    Kills an impl that blindly computes 0.5^(age/0).
    """
    hits = [MemoryHit(memory="a", relevance=0.5, age_days=5.0)]
    # Should not raise — implementation must guard against half_life=0
    result = decay_weighted_rank(hits, now_ts=_NOW, half_life_days=0.0)
    # With half_life=0: age>0 → fully decayed (score≈0), age=0 → score=relevance
    assert len(result) == 1  # no crash


# ---------------------------------------------------------------------------
# Ordering stability
# ---------------------------------------------------------------------------


def test_tie_breaking_stable() -> None:
    """Equal scores → stable order (input order preserved).

    Kills an impl with non-deterministic tie-breaking.
    """
    # Same relevance, same age → same score → order should be stable (input order).
    hits = [
        MemoryHit(memory="first", relevance=0.5, age_days=5.0),
        MemoryHit(memory="second", relevance=0.5, age_days=5.0),
    ]
    results = decay_weighted_rank(hits, now_ts=_NOW, half_life_days=7.0)
    memories = [r.memory for r in results]
    assert memories == ["first", "second"], (
        f"Tie-breaking must preserve input order; got {memories}"
    )
