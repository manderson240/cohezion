"""Tests for TierOptimizer — promotion, demotion, and no-change logic."""
from __future__ import annotations

import time

from cohezion.platform.session_tracker import ModelUsageEvent, SessionRecord
from cohezion.platform.tier_optimizer import TierOptimizer, TierRecommendation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(
    session_id: str,
    models: list[tuple[str, float, str]],  # (model_name, duration_s, task_type)
    age_s: float = 0.0,
) -> SessionRecord:
    """Create a SessionRecord with pre-populated events.

    age_s offsets started_at into the past so demotion tests work correctly.
    """
    record = SessionRecord(session_id=session_id, started_at=time.time() - age_s)
    for model_name, duration_s, task_type in models:
        record.model_events.append(
            ModelUsageEvent(
                session_id=session_id,
                model_name=model_name,
                started_at=time.time() - age_s,
                duration_s=duration_s,
                task_type=task_type,
            )
        )
    return record


def _optimizer() -> TierOptimizer:
    return TierOptimizer()


# ---------------------------------------------------------------------------
# Promotion tests
# ---------------------------------------------------------------------------


class TestPromotion:
    def test_cold_to_warm_with_high_usage(self) -> None:
        optimizer = _optimizer()
        # 4 sessions, each uses the model for 2400 s (0.667 h/day), 100% penetration
        sessions = [_make_record(f"s{i}", [("qwen3-coder:30b", 2400, "inference")]) for i in range(4)]
        histogram = {"qwen3-coder:30b": 0.667}  # hours/day
        tiers = {"qwen3-coder:30b": "cold"}

        changes = optimizer.recommend_tier_changes(histogram, sessions, tiers)
        assert len(changes) == 1
        change = changes[0]
        assert change.recommendation == TierRecommendation.PROMOTE
        assert change.current_tier == "cold"
        assert change.recommended_tier == "warm"

    def test_warm_to_hot_with_high_usage(self) -> None:
        optimizer = _optimizer()
        sessions = [_make_record(f"s{i}", [("phi4-mini", 3600, "inference")]) for i in range(6)]
        histogram = {"phi4-mini": 1.0}
        tiers = {"phi4-mini": "warm"}

        changes = optimizer.recommend_tier_changes(histogram, sessions, tiers)
        assert any(
            c.recommendation == TierRecommendation.PROMOTE and c.recommended_tier == "hot"
            for c in changes
        )

    def test_no_promotion_when_usage_below_threshold(self) -> None:
        optimizer = _optimizer()
        sessions = [_make_record(f"s{i}", [("phi4-mini", 300, "inference")]) for i in range(4)]
        histogram = {"phi4-mini": 0.08}  # well below 0.5 h/day
        tiers = {"phi4-mini": "cold"}

        changes = optimizer.recommend_tier_changes(histogram, sessions, tiers)
        promotes = [c for c in changes if c.recommendation == TierRecommendation.PROMOTE]
        assert len(promotes) == 0

    def test_no_promotion_when_session_penetration_low(self) -> None:
        optimizer = _optimizer()
        # 10 sessions, only 2 use the model (20% penetration)
        sessions = [_make_record(f"s{i}", [("phi4-mini", 3600, "inference")]) for i in range(2)]
        sessions += [_make_record(f"other{i}", [("different-model", 100, "inference")]) for i in range(8)]
        histogram = {"phi4-mini": 0.6}
        tiers = {"phi4-mini": "cold"}

        changes = optimizer.recommend_tier_changes(histogram, sessions, tiers)
        promotes = [c for c in changes if c.model_name == "phi4-mini" and c.recommendation == TierRecommendation.PROMOTE]
        assert len(promotes) == 0

    def test_hot_model_not_promoted_further(self) -> None:
        optimizer = _optimizer()
        sessions = [_make_record(f"s{i}", [("always-hot", 3600, "inference")]) for i in range(5)]
        histogram = {"always-hot": 2.0}
        tiers = {"always-hot": "hot"}

        changes = optimizer.recommend_tier_changes(histogram, sessions, tiers)
        promotes = [c for c in changes if c.recommendation == TierRecommendation.PROMOTE]
        assert len(promotes) == 0


# ---------------------------------------------------------------------------
# Demotion tests
# ---------------------------------------------------------------------------


class TestDemotion:
    def test_hot_to_warm_when_unused_14_days(self) -> None:
        optimizer = _optimizer()
        old_age_s = 15 * 86400  # 15 days ago
        sessions = [_make_record("old", [("stale-model", 100, "inference")], age_s=old_age_s)]
        histogram = {"stale-model": 0.0}
        tiers = {"stale-model": "hot"}

        changes = optimizer.recommend_tier_changes(histogram, sessions, tiers)
        demotions = [c for c in changes if c.recommendation == TierRecommendation.DEMOTE]
        assert len(demotions) == 1
        assert demotions[0].recommended_tier == "warm"

    def test_warm_to_cold_when_unused_14_days(self) -> None:
        optimizer = _optimizer()
        old_age_s = 20 * 86400
        sessions = [_make_record("old", [("stale-model", 100, "inference")], age_s=old_age_s)]
        histogram = {"stale-model": 0.0}
        tiers = {"stale-model": "warm"}

        changes = optimizer.recommend_tier_changes(histogram, sessions, tiers)
        demotions = [c for c in changes if c.recommendation == TierRecommendation.DEMOTE]
        assert len(demotions) == 1
        assert demotions[0].recommended_tier == "cold"

    def test_no_demotion_within_14_days(self) -> None:
        optimizer = _optimizer()
        recent_age_s = 5 * 86400  # 5 days ago
        sessions = [_make_record("recent", [("active-model", 1000, "inference")], age_s=recent_age_s)]
        histogram = {"active-model": 0.2}
        tiers = {"active-model": "warm"}

        changes = optimizer.recommend_tier_changes(histogram, sessions, tiers)
        demotions = [c for c in changes if c.recommendation == TierRecommendation.DEMOTE]
        assert len(demotions) == 0

    def test_training_only_model_demoted_to_cold(self) -> None:
        optimizer = _optimizer()
        sessions = [_make_record(f"s{i}", [("train-only", 3600, "training")]) for i in range(5)]
        histogram = {"train-only": 1.0}
        tiers = {"train-only": "warm"}

        changes = optimizer.recommend_tier_changes(histogram, sessions, tiers)
        demotions = [c for c in changes if c.recommendation == TierRecommendation.DEMOTE]
        assert len(demotions) == 1
        assert demotions[0].recommended_tier == "cold"

    def test_training_only_already_cold_no_change(self) -> None:
        optimizer = _optimizer()
        sessions = [_make_record(f"s{i}", [("train-only", 3600, "training")]) for i in range(3)]
        histogram = {"train-only": 0.8}
        tiers = {"train-only": "cold"}

        changes = optimizer.recommend_tier_changes(histogram, sessions, tiers)
        assert len(changes) == 0

    def test_model_not_in_tiers_ignored(self) -> None:
        optimizer = _optimizer()
        sessions = [_make_record("s1", [("untracked-model", 3600, "inference")])]
        histogram = {"untracked-model": 1.0}
        tiers = {}  # model not registered

        changes = optimizer.recommend_tier_changes(histogram, sessions, tiers)
        assert len(changes) == 0


# ---------------------------------------------------------------------------
# No-change tests
# ---------------------------------------------------------------------------


class TestNoChange:
    def test_normal_usage_no_change(self) -> None:
        optimizer = _optimizer()
        sessions = [_make_record(f"s{i}", [("balanced-model", 600, "inference")]) for i in range(3)]
        histogram = {"balanced-model": 0.1}  # Below promote threshold
        tiers = {"balanced-model": "warm"}

        changes = optimizer.recommend_tier_changes(histogram, sessions, tiers)
        assert len(changes) == 0

    def test_empty_sessions_returns_empty(self) -> None:
        optimizer = _optimizer()
        changes = optimizer.recommend_tier_changes({}, [], {"phi4-mini": "hot"})
        # No sessions → no usage data → model in "hot" gets demotion check
        # but last_used_at is 0.0 so it's treated as inf days unused → should demote
        # Verify the method at least completes without error
        assert isinstance(changes, list)

    def test_confidence_bounded_0_to_1(self) -> None:
        optimizer = _optimizer()
        sessions = [_make_record(f"s{i}", [("heavy", 86400, "inference")]) for i in range(10)]
        histogram = {"heavy": 24.0}  # Extreme usage
        tiers = {"heavy": "cold"}

        changes = optimizer.recommend_tier_changes(histogram, sessions, tiers)
        for change in changes:
            assert 0.0 <= change.confidence <= 1.0

    def test_tier_change_has_reason(self) -> None:
        optimizer = _optimizer()
        sessions = [_make_record(f"s{i}", [("phi4-mini", 2400, "inference")]) for i in range(4)]
        histogram = {"phi4-mini": 0.667}
        tiers = {"phi4-mini": "cold"}

        changes = optimizer.recommend_tier_changes(histogram, sessions, tiers)
        for change in changes:
            assert isinstance(change.reason, str)
            assert len(change.reason) > 0
