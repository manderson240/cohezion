"""Item 109: Recency-decay weighting on memory recall.

``decay_weighted_rank`` re-ranks ``MemoryHit`` objects by
``relevance * 0.5 ** (age_days / half_life_days)`` — the standard exponential-decay
recall used by persistent-agent memories (distilled from Marktechpost tutorial,
2026-06-06, ``docs/research/TUTORIAL_DISTILLATION_2026-06-06.md``).

Addresses the gap in cohezion recall (item-108): currently ranked by RELEVANCE only,
so a stale-but-similar memory outranks a fresh one.  This scorer applies a decay
multiplier and returns a re-ranked list — **without deleting any hit** (decay is a
RANKING weight, not eviction — non-destructive, consistent with non-destructive-wiring).

Pure (injected hits + now_ts; no wall-clock read under pytest).  Report-only scorer.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryHit:
    """A recalled memory with its relevance score and age (item 109).

    Attributes
    ----------
    memory:
        The recalled content — any object (str, dict, dataclass, …).
    relevance:
        Cosine / embedding similarity score in [0, 1] (or any non-negative float).
    age_days:
        How many days old the memory is relative to the caller's ``now_ts``.
        Pre-computed by the caller from ``(now_ts - created_ts) / 86_400`` or
        provided directly.  Must be ≥ 0.
    """

    memory: object
    relevance: float
    age_days: float


@dataclass(frozen=True)
class RankedHit:
    """A ``MemoryHit`` with its computed decay-weighted score (item 109).

    Attributes
    ----------
    memory:
        The recalled content (forwarded from the input hit).
    relevance:
        Original relevance score (forwarded unchanged).
    age_days:
        Original age (forwarded unchanged).
    score:
        ``relevance * 0.5 ** (age_days / half_life_days)`` — used for ranking.
        Higher is better.
    """

    memory: object
    relevance: float
    age_days: float
    score: float


def decay_weighted_rank(
    hits: list[MemoryHit],
    *,
    now_ts: float,
    half_life_days: float,
) -> list[RankedHit]:
    """Re-rank memory hits by exponential recency decay (item 109). Pure.

    Applies the standard persistent-memory decay formula to each hit and returns
    the list sorted by the decay-weighted score descending (highest-score first).
    Hits with equal scores are returned in stable (input) order.

    The formula::

        score = relevance * 0.5 ** (age_days / half_life_days)

    At ``half_life_days → ∞``: exponent → 0, score → relevance (pure relevance order).
    At ``age_days == 0``: decay factor = 1.0, score = relevance (no penalty for fresh hits).
    At ``half_life_days == 0``: any hit with ``age_days > 0`` has score = 0 (instantly
    stale); hits with ``age_days == 0`` retain their relevance score.  This edge case
    is handled gracefully (no ZeroDivisionError).

    Args:
        hits:
            List of :class:`MemoryHit` to re-rank.  May be empty.
        now_ts:
            Injected "current" Unix timestamp (float).  Used by callers to compute
            ``age_days`` from absolute timestamps without calling ``time.time()``.
            Not used directly in the scoring formula — the age is already in the hit.
        half_life_days:
            Number of days after which a hit's score is halved (holding relevance
            constant).  Must be ≥ 0.  Pass a very large value (e.g. ``1e15``) to
            effectively disable decay and rank by pure relevance.

    Returns:
        List of :class:`RankedHit` sorted by ``score`` descending.  Stable sort
        preserves input order for ties.  Empty ``hits`` → ``[]``.

    Pure (no writes, no clock calls, no DB).  Report-only scorer.
    """
    if not hits:
        return []

    ranked: list[RankedHit] = []
    for hit in hits:
        if half_life_days == 0.0:
            # Edge-case guard: avoid 0.5^(age/0) = 0.5^inf → 0 for age>0 without ZeroDivision
            decay = 1.0 if hit.age_days == 0.0 else 0.0
        else:
            decay = 0.5 ** (hit.age_days / half_life_days)
        ranked.append(
            RankedHit(
                memory=hit.memory,
                relevance=hit.relevance,
                age_days=hit.age_days,
                score=hit.relevance * decay,
            )
        )

    # Stable descending sort: higher score first; ties preserve input order.
    return sorted(ranked, key=lambda r: r.score, reverse=True)
