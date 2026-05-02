"""Skill refinement validator — measures before/after performance of skill mutations.

Closes W1 in the strategic plan: the SkillRefiner mutated skill definitions without
validating that mutations actually improved performance. This validator records
pre-mutation baselines and blocks regressions before they propagate.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime


logger = logging.getLogger(__name__)


@dataclass
class RefinementMetrics:
    success_rate: float  # 0-1
    avg_latency_ms: float
    avg_coherence: float
    sample_count: int
    measured_at: str  # ISO timestamp

    @staticmethod
    def now_iso() -> str:
        return datetime.now(UTC).isoformat()


class SkillRefinementValidator:
    """Validate that skill mutations improve (or at least don't degrade) performance."""

    def __init__(self, min_samples: int = 5, max_degradation_pct: float = 5.0) -> None:
        self._min_samples = min_samples
        self._max_degradation_pct = max_degradation_pct
        self._baseline_metrics: dict[str, RefinementMetrics] = {}

    def record_baseline(self, skill_name: str, metrics: RefinementMetrics) -> None:
        """Record pre-mutation baseline metrics for a skill."""
        self._baseline_metrics[skill_name] = metrics
        logger.info(
            "Baseline recorded for %s: success=%.1f%% coherence=%.3f samples=%d",
            skill_name,
            metrics.success_rate * 100,
            metrics.avg_coherence,
            metrics.sample_count,
        )
        self._persist_async(skill_name, "baseline", metrics)

    def validate_refinement(
        self, skill_name: str, post_metrics: RefinementMetrics
    ) -> tuple[bool, str]:
        """Compare post-mutation metrics against baseline.

        Returns (approved, reason).
        Blocks mutations that degrade success_rate or coherence by > max_degradation_pct.
        """
        if skill_name not in self._baseline_metrics:
            reason = f"no baseline recorded for '{skill_name}'"
            logger.warning("Validation skipped: %s", reason)
            return False, reason

        if post_metrics.sample_count < self._min_samples:
            reason = (
                f"insufficient samples: got {post_metrics.sample_count}, need {self._min_samples}"
            )
            logger.warning("Validation blocked for %s: %s", skill_name, reason)
            return False, reason

        baseline = self._baseline_metrics[skill_name]
        threshold = self._max_degradation_pct / 100.0

        success_drop = baseline.success_rate - post_metrics.success_rate
        if success_drop > threshold:
            reason = (
                f"success_rate degraded by {success_drop:.1%} "
                f"(baseline={baseline.success_rate:.1%}, "
                f"post={post_metrics.success_rate:.1%}, "
                f"max_allowed={threshold:.1%})"
            )
            logger.warning("Refinement REJECTED for %s: %s", skill_name, reason)
            return False, reason

        coherence_drop = baseline.avg_coherence - post_metrics.avg_coherence
        if coherence_drop > threshold:
            reason = (
                f"avg_coherence degraded by {coherence_drop:.3f} "
                f"(baseline={baseline.avg_coherence:.3f}, "
                f"post={post_metrics.avg_coherence:.3f}, "
                f"max_allowed={threshold:.3f})"
            )
            logger.warning("Refinement REJECTED for %s: %s", skill_name, reason)
            return False, reason

        logger.info(
            "Refinement APPROVED for %s: success %.1f%%→%.1f%%, coherence %.3f→%.3f",
            skill_name,
            baseline.success_rate * 100,
            post_metrics.success_rate * 100,
            baseline.avg_coherence,
            post_metrics.avg_coherence,
        )
        return True, "improved"

    def get_improvement_report(self, skill_name: str) -> dict:
        """Return before/after comparison dict for a skill."""
        if skill_name not in self._baseline_metrics:
            return {"skill_name": skill_name, "error": "no baseline recorded"}

        baseline = self._baseline_metrics[skill_name]
        return {
            "skill_name": skill_name,
            "baseline": {
                "success_rate": baseline.success_rate,
                "avg_latency_ms": baseline.avg_latency_ms,
                "avg_coherence": baseline.avg_coherence,
                "sample_count": baseline.sample_count,
                "measured_at": baseline.measured_at,
            },
        }

    def _persist_async(self, skill_name: str, stage: str, metrics: RefinementMetrics) -> None:
        """Non-blocking SurrealDB persistence — failures must not crash callers."""
        try:
            import asyncio

            async def _write() -> None:
                from cohezion.persistence.surreal_client import get_surreal_client

                async with get_surreal_client() as db:
                    await db.create(
                        "skill_refinement_metric",
                        {
                            "skill_name": skill_name,
                            "stage": stage,
                            "success_rate": metrics.success_rate,
                            "avg_latency_ms": metrics.avg_latency_ms,
                            "avg_coherence": metrics.avg_coherence,
                            "sample_count": metrics.sample_count,
                            "measured_at": metrics.measured_at,
                        },
                    )

            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_write())
            else:
                loop.run_until_complete(_write())

        except Exception:
            logger.debug(
                "SurrealDB persistence skipped for %s/%s (non-blocking)", skill_name, stage
            )
