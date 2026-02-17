"""
Charter-aligned skill effectiveness scoring.
Primary weight on HIHO stability (0.5 coherence baseline).
"""

import logging
from datetime import datetime, timedelta

from pydantic import BaseModel

from cohezion.core.persistence.surreal_client import get_surreal_client


logger = logging.getLogger(__name__)


class CharterSkillScore(BaseModel):
    """Skill score with Charter-aligned metrics."""

    skill_name: str
    usage_count: int
    success_rate: float  # 0-1
    token_efficiency: float  # outcomes per token
    avg_coherence: float  # Average coherence
    hiho_stability: float  # ★ PRIMARY METRIC: How close to 0.5?
    effectiveness_score: float  # Charter-weighted composite


class CharterAlignedSkillScorer:
    """Calculate skill effectiveness with HIHO weighting."""

    def __init__(self):
        self.db = get_surreal_client()
        self.target_coherence = 0.5  # Charter mandated

    async def calculate_daily_scores(self, date: datetime) -> list[CharterSkillScore]:
        """Calculate Charter-aligned effectiveness scores."""

        # Query all skill usage for the day
        result = await self.db.query(
            """
            SELECT
                skill_name,
                count() as usage_count,
                math::sum(tokens_used) as total_tokens,
                math::sum(success) as success_count,
                math::mean(coherence_score) as avg_coherence,
                math::sum(hiho_stable) as hiho_stable_count
            FROM skill_usage
            WHERE invoked_at >= type::datetime($start_date)
              AND invoked_at < type::datetime($end_date)
            GROUP BY skill_name
            ORDER BY usage_count DESC;
        """,
            {
                "start_date": date.isoformat(),
                "end_date": (date + timedelta(days=1)).isoformat(),
            },
        )

        scores = []
        for row in result:
            usage_count = row["usage_count"]
            success_count = row["success_count"]
            total_tokens = row["total_tokens"]
            avg_coherence = row["avg_coherence"]
            hiho_stable_count = row["hiho_stable_count"]

            # Standard metrics
            success_rate = success_count / usage_count if usage_count > 0 else 0
            token_efficiency = success_count / total_tokens if total_tokens > 0 else 0

            # CHARTER METRIC: HIHO Stability
            # How close is average coherence to 0.5?
            hiho_delta = abs(avg_coherence - self.target_coherence)
            hiho_stability_distance = max(0.0, 1.0 - (hiho_delta * 2))  # 1.0 at perfect 0.5

            # Alternative: Percentage of executions that were HIHO stable
            hiho_stability_rate = hiho_stable_count / usage_count if usage_count > 0 else 0

            # Use whichever is higher (most charitable scoring)
            hiho_stability = max(hiho_stability_distance, hiho_stability_rate)

            # CHARTER-ALIGNED COMPOSITE SCORE
            # HIHO stability gets HIGHEST weight (50%)
            effectiveness_score = (
                0.50 * hiho_stability
                + 0.25 * success_rate  # ★ Charter primary  # Reduced from 40%
                + 0.25 * token_efficiency
            )  # Reduced from 30%

            scores.append(
                CharterSkillScore(
                    skill_name=row["skill_name"],
                    usage_count=usage_count,
                    success_rate=success_rate,
                    token_efficiency=token_efficiency,
                    avg_coherence=avg_coherence,
                    hiho_stability=hiho_stability,
                    effectiveness_score=effectiveness_score,
                )
            )

        # Persist to skill_metrics table
        for score in scores:
            await self._persist_metric(date, score)

        return scores

    async def _persist_metric(self, date: datetime, score: CharterSkillScore):
        """Persist Charter-aligned metric."""
        try:
            await self.db.query(
                """
                CREATE skill_metrics_charter CONTENT {
                    skill_name: $skill_name,
                    date: $date,
                    usage_count: $usage_count,
                    success_rate: $success_rate,
                    token_efficiency: $token_efficiency,
                    avg_coherence: $avg_coherence,
                    hiho_stability: $hiho_stability,
                    effectiveness_score: $effectiveness_score
                };
            """,
                {
                    "skill_name": score.skill_name,
                    "date": date.isoformat(),
                    "usage_count": score.usage_count,
                    "success_rate": score.success_rate,
                    "token_efficiency": score.token_efficiency,
                    "avg_coherence": score.avg_coherence,
                    "hiho_stability": score.hiho_stability,
                    "effectiveness_score": score.effectiveness_score,
                },
            )
        except Exception as e:
            logger.warning("Failed to persist skill metric to SurrealDB: %s", e)

    async def get_trending_skills(self, days: int = 7, limit: int = 10) -> list[CharterSkillScore]:
        """Get top skills by Charter-aligned effectiveness over time period."""

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        result = await self.db.query(
            """
            SELECT
                skill_name,
                math::sum(usage_count) as total_usage,
                math::mean(success_rate) as avg_success,
                math::mean(token_efficiency) as avg_efficiency,
                math::mean(avg_coherence) as avg_coherence,
                math::mean(hiho_stability) as avg_hiho_stability,
                math::mean(effectiveness_score) as avg_effectiveness
            FROM skill_metrics_charter
            WHERE date >= type::datetime($start_date)
              AND date < type::datetime($end_date)
            GROUP BY skill_name
            ORDER BY avg_effectiveness DESC
            LIMIT $limit;
        """,
            {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "limit": limit,
            },
        )

        trending = []
        for row in result:
            trending.append(
                CharterSkillScore(
                    skill_name=row["skill_name"],
                    usage_count=int(row["total_usage"]),
                    success_rate=row["avg_success"],
                    token_efficiency=row["avg_efficiency"],
                    avg_coherence=row["avg_coherence"],
                    hiho_stability=row["avg_hiho_stability"],
                    effectiveness_score=row["avg_effectiveness"],
                )
            )

        return trending


# Singleton accessor
_skill_scorer = None


def get_skill_scorer() -> CharterAlignedSkillScorer:
    """Get global Charter-aligned skill scorer instance."""
    global _skill_scorer
    if _skill_scorer is None:
        _skill_scorer = CharterAlignedSkillScorer()
    return _skill_scorer


def reset_skill_scorer():
    """Reset global skill scorer (for testing)."""
    global _skill_scorer
    _skill_scorer = None
