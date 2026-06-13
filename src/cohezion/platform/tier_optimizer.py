# math/physics symbols intentional
"""Data-driven model tier optimization based on cross-session usage."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)

# Tier name constants matching ModelTierPolicy enum values in model_pool_config.py
_HOT = "hot"
_WARM = "warm"
_COLD = "cold"

_TIER_ORDER = {_HOT: 2, _WARM: 1, _COLD: 0}


class TierRecommendation(Enum):
    PROMOTE = "promote"  # Move to higher tier (COLD→WARM, WARM→HOT)
    DEMOTE = "demote"  # Move to lower tier
    KEEP = "keep"  # No change


@dataclass
class TierChange:
    model_name: str
    current_tier: str
    recommended_tier: str
    reason: str
    recommendation: TierRecommendation
    confidence: float  # 0.0 – 1.0


class TierOptimizer:
    """Usage-histogram-driven tier reassignment recommendations.

    Rules applied in priority order:
    1. Model used exclusively for training (never inference) → keep in COLD.
    2. Model used >30 min/day avg AND appears in >50% of recent sessions → promote.
    3. Model unused for >14 days → demote.
    4. Otherwise → keep.
    """

    PROMOTE_THRESHOLD_HOURS: float = 0.5  # 30 min/day avg
    PROMOTE_SESSION_PCT: float = 0.5  # 50% of sessions must have used it
    DEMOTE_UNUSED_DAYS: int = 14

    def recommend_tier_changes(
        self,
        usage_histogram: dict[str, float],  # model → hours/day (7-day avg)
        session_records: list,  # list[SessionRecord]
        current_tiers: dict[str, str],  # model → "hot"|"warm"|"cold"
    ) -> list[TierChange]:
        """Return a list of suggested tier changes.

        Only models already present in current_tiers are evaluated.
        """
        changes: list[TierChange] = []

        total_sessions = len(session_records)
        # Build per-model session penetration set
        session_per_model: dict[str, set[str]] = {}
        for record in session_records:
            for ev in record.model_events:
                session_per_model.setdefault(ev.model_name, set()).add(record.session_id)

        # Build per-model task-type breakdown
        inference_sessions: dict[str, set[str]] = {}
        training_sessions: dict[str, set[str]] = {}
        newest_use: dict[str, float] = {}
        for record in session_records:
            for ev in record.model_events:
                m = ev.model_name
                if ev.task_type == "inference":
                    inference_sessions.setdefault(m, set()).add(record.session_id)
                else:
                    training_sessions.setdefault(m, set()).add(record.session_id)
                newest_use[m] = max(newest_use.get(m, 0.0), ev.started_at)

        for model, current_tier in current_tiers.items():
            change = self._evaluate_model(
                model=model,
                current_tier=current_tier,
                hours_per_day=usage_histogram.get(model, 0.0),
                total_sessions=total_sessions,
                sessions_used=len(session_per_model.get(model, set())),
                has_inference=bool(inference_sessions.get(model)),
                has_only_training=(
                    bool(training_sessions.get(model)) and not inference_sessions.get(model)
                ),
                last_used_at=newest_use.get(model, 0.0),
            )
            if change is not None:
                changes.append(change)

        return changes

    def _evaluate_model(
        self,
        model: str,
        current_tier: str,
        hours_per_day: float,
        total_sessions: int,
        sessions_used: int,
        has_inference: bool,
        has_only_training: bool,
        last_used_at: float,
    ) -> TierChange | None:
        """Evaluate a single model and return a TierChange or None."""

        # Rule 1: training-only models stay in COLD regardless of usage volume
        if has_only_training:
            if current_tier != _COLD:
                return TierChange(
                    model_name=model,
                    current_tier=current_tier,
                    recommended_tier=_COLD,
                    reason="Model used exclusively for training; inference tier not warranted.",
                    recommendation=TierRecommendation.DEMOTE,
                    confidence=0.9,
                )
            return None  # Already COLD, keep

        # Rule 2: high-traffic promotion candidate
        session_pct = (sessions_used / total_sessions) if total_sessions > 0 else 0.0
        if (
            hours_per_day >= self.PROMOTE_THRESHOLD_HOURS
            and session_pct >= self.PROMOTE_SESSION_PCT
            and has_inference
        ):
            target = self._next_tier_up(current_tier)
            if target != current_tier:
                confidence = (
                    min(
                        1.0,
                        (hours_per_day / self.PROMOTE_THRESHOLD_HOURS) * 0.5
                        + (session_pct / self.PROMOTE_SESSION_PCT) * 0.5,
                    )
                    * 0.95
                )
                return TierChange(
                    model_name=model,
                    current_tier=current_tier,
                    recommended_tier=target,
                    reason=(
                        f"High usage: {hours_per_day:.2f} h/day avg, {session_pct:.0%} session penetration."
                    ),
                    recommendation=TierRecommendation.PROMOTE,
                    confidence=round(confidence, 3),
                )
            return None  # Already HOT

        # Rule 3: unused demotion
        days_since_use = (time.time() - last_used_at) / 86400 if last_used_at > 0 else float("inf")
        if days_since_use > self.DEMOTE_UNUSED_DAYS:
            target = self._next_tier_down(current_tier)
            if target != current_tier:
                confidence = min(1.0, days_since_use / (self.DEMOTE_UNUSED_DAYS * 2))
                return TierChange(
                    model_name=model,
                    current_tier=current_tier,
                    recommended_tier=target,
                    reason=(
                        f"Unused for {days_since_use:.0f} days (threshold: {self.DEMOTE_UNUSED_DAYS} days)."
                    ),
                    recommendation=TierRecommendation.DEMOTE,
                    confidence=round(confidence, 3),
                )

        return None  # No change warranted

    @staticmethod
    def _next_tier_up(tier: str) -> str:
        if tier == _COLD:
            return _WARM
        if tier == _WARM:
            return _HOT
        return _HOT

    @staticmethod
    def _next_tier_down(tier: str) -> str:
        if tier == _HOT:
            return _WARM
        if tier == _WARM:
            return _COLD
        return _COLD
