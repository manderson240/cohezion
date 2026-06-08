"""Recency-decay recall re-ranking (item 109, 2026-06-08) — report-only pure scorer.

Distilled by LOCAL inference from a Marktechpost persistent-memory tutorial — the ONE genuine lever
of that batch (``docs/research/TUTORIAL_DISTILLATION_2026-06-06.md``): cohezion recall (item-29
``recall_neurons`` / item-108 recall) ranks by RELEVANCE only, so a stale-but-similar memory
outranks a fresh one. This applies the standard exponential-decay recall weight
``relevance * 0.5**(age_days/half_life)`` as a RANKING weight — never eviction (non-destructive).

Lives in its own module because both natural homes (``knowledge_bridge`` 564 LOC, ``simplicity_audit``
501 LOC) already exceed the 500-line hard limit; this is the additive-composition move (INSIGHTS #11),
not a new home for new state. The wiring target (named in item 109) is the item-108 recall +
``recall_neurons``, which CONSUME this pure scorer.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


_SECONDS_PER_DAY = 86400.0


@dataclass(frozen=True)
class DecayRankedHit:
    """One recall hit with its recency-decayed score. ``memory`` is opaque (the recalled item)."""

    memory: Any
    relevance: float
    age_days: float
    score: float  # relevance * 0.5 ** (age_days / half_life_days)


def decay_weighted_rank(
    hits: Iterable[tuple[Any, float, float]],
    *,
    now_ts: float,
    half_life_days: float,
) -> list[DecayRankedHit]:
    """Re-rank recall hits by ``relevance * exponential recency decay`` (item 109). Pure scorer.

    Each hit is ``(memory, relevance, timestamp_seconds)``. The age in days is computed from the
    INJECTED ``now_ts`` (so there is NO clock read under pytest):
    ``age_days = max(0, (now_ts - timestamp) / 86400)`` — a future-dated memory is clamped to age 0
    (no boost). The score is ``relevance * 0.5 ** (age_days / half_life_days)``: relevance DOMINATES,
    decay MODULATES. ``half_life_days = inf`` turns decay OFF (score == relevance — pure-relevance
    ranking); a non-positive half-life is degenerate and treated as fully decayed (score 0, no
    crash). Hits are returned sorted by score DESCENDING (ties broken by lower age, then higher
    relevance). Empty → ``[]``. Never deletes a memory — decay is a ranking weight, not eviction
    (non-destructive). Pure: injected hits + ``now_ts``, no I/O, no clock.
    """
    ranked: list[DecayRankedHit] = []
    for memory, relevance, ts in hits:
        age_days = max(0.0, (now_ts - float(ts)) / _SECONDS_PER_DAY)
        # half_life == inf → age/inf == 0 → decay 1.0; non-positive half-life is degenerate →
        # fully decayed (score 0, no ZeroDivision).
        decay = 0.5 ** (age_days / half_life_days) if half_life_days > 0 else 0.0
        rel = float(relevance)
        ranked.append(
            DecayRankedHit(memory=memory, relevance=rel, age_days=age_days, score=rel * decay)
        )
    ranked.sort(key=lambda h: (-h.score, h.age_days, -h.relevance))
    return ranked
