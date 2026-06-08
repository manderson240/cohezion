"""Discriminating tests for decay_weighted_rank (backlog item 109, 2026-06-08).

`decay_weighted_rank(hits, *, now_ts, half_life_days)` re-ranks recall hits
`(memory, relevance, timestamp)` by `relevance * 0.5**(age_days/half_life)` where age is computed
from the injected now_ts. Relevance dominates, decay modulates. Report-only pure scorer; never
deletes a memory (decay is a ranking weight, not eviction).

Each test fails a plausible wrong impl:
  - an impl that sorts by RELEVANCE only (ignores age) → test_equal_relevance_fresher_wins,
  - an impl that lets decay override relevance → test_relevance_dominates_decay_modulates,
  - an impl that always applies decay even when off → test_infinite_half_life_pure_relevance,
  - an impl that does NOT clamp a future timestamp (boosts it) → test_future_timestamp_no_boost.
"""

from __future__ import annotations

from cohezion.governance.recall_ranking import DecayRankedHit, decay_weighted_rank


_DAY = 86400.0
_NOW = 1_000_000_000.0  # fixed injected "now" — no clock under pytest


def test_empty_returns_empty() -> None:
    assert decay_weighted_rank([], now_ts=_NOW, half_life_days=7.0) == []


def test_equal_relevance_fresher_wins() -> None:
    # DISCRIMINATING: equal relevance, different age → the FRESHER memory ranks first. An impl that
    # sorts by relevance only would tie (and not reorder by freshness).
    fresh = ("fresh", 0.8, _NOW - 1 * _DAY)
    stale = ("stale", 0.8, _NOW - 10 * _DAY)
    out = decay_weighted_rank([stale, fresh], now_ts=_NOW, half_life_days=7.0)
    assert [h.memory for h in out] == ["fresh", "stale"]
    assert out[0].score > out[1].score


def test_relevance_dominates_decay_modulates() -> None:
    # A much-higher-relevance OLD hit (one half-life old → x0.5) still beats a barely-relevant fresh
    # hit: 0.9*0.5 = 0.45 > 0.2*1.0 = 0.2.
    old_strong = ("old_strong", 0.9, _NOW - 7 * _DAY)
    fresh_weak = ("fresh_weak", 0.2, _NOW)
    out = decay_weighted_rank([fresh_weak, old_strong], now_ts=_NOW, half_life_days=7.0)
    assert out[0].memory == "old_strong"
    assert out[0].score == 0.45
    assert out[1].score == 0.2


def test_infinite_half_life_pure_relevance() -> None:
    # DISCRIMINATING: half_life = inf turns decay OFF → ranking is pure relevance regardless of age.
    old_strong = ("old_strong", 0.9, _NOW - 1000 * _DAY)
    fresh_weak = ("fresh_weak", 0.5, _NOW)
    out = decay_weighted_rank([fresh_weak, old_strong], now_ts=_NOW, half_life_days=float("inf"))
    assert [h.memory for h in out] == ["old_strong", "fresh_weak"]
    assert out[0].score == 0.9 and out[1].score == 0.5  # score == relevance (decay off)


def test_future_timestamp_no_boost() -> None:
    # DISCRIMINATING: a future-dated memory is clamped to age 0 — it must NOT outscore an equally
    # relevant present memory. An impl that doesn't clamp gives 0.5**(negative) > 1 (a boost).
    future = ("future", 0.5, _NOW + 5 * _DAY)
    present = ("present", 0.5, _NOW)
    out = decay_weighted_rank([future, present], now_ts=_NOW, half_life_days=7.0)
    assert out[0].score == out[1].score == 0.5  # both age 0, no boost
    assert all(h.age_days == 0.0 for h in out)


def test_nonpositive_half_life_no_crash() -> None:
    # A degenerate half_life <= 0 must not ZeroDivision; it fully decays (score 0).
    out = decay_weighted_rank([("m", 0.9, _NOW - _DAY)], now_ts=_NOW, half_life_days=0.0)
    assert isinstance(out[0], DecayRankedHit)
    assert out[0].score == 0.0


def test_age_days_computed_from_now_ts() -> None:
    out = decay_weighted_rank([("m", 1.0, _NOW - 3 * _DAY)], now_ts=_NOW, half_life_days=3.0)
    assert out[0].age_days == 3.0
    assert out[0].score == 0.5  # one half-life → 1.0 * 0.5
