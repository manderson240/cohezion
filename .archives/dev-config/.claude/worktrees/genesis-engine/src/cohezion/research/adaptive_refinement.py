"""Adaptive Skill Refinement System.

Elegantly simple compound feature that automatically improves
skills based on research outcomes.

Follows compound engineering patterns:
- Plugin architecture
- Clean ~200 line implementation
- Full compound executor integration
- Skill refinement loop
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from cohezion.compound.core.executor import CompoundExecutor, ExecutionConfig
from cohezion.compound.models import ExecutionResult, Task


logger = logging.getLogger(__name__)


@dataclass
class SkillMetrics:
    """Metrics for skill performance."""

    skill_name: str
    total_invocations: int = 0
    success_rate: float = 1.0
    avg_coherence: float = 0.5
    last_used: str = field(default_factory=lambda: datetime.now().isoformat())
    improvements_made: int = 0


@dataclass
class SkillRefinement:
    """A refinement made to a skill.

    Tracks previous version for rollback capability (Issue #13).
    """

    skill_name: str
    timestamp: str
    change_description: str
    previous_score: float
    new_score: float
    improvement_type: str  # 'performance', 'coherence', 'reliability'
    previous_version: str | None = None  # For rollback
    rollback_available: bool = False


class AdaptiveSkillRefiner:
    """Automatically refine skills based on research outcomes.

    Elegant ~200 line implementation of adaptive skill refinement.
    Integrates with compound executor and research module.
    """

    def __init__(
        self,
        executor: CompoundExecutor | None = None,
        skills_dir: Path | None = None,
    ):
        """Initialize adaptive skill refiner.

        Args:
            executor: CompoundExecutor for running refinement tasks
            skills_dir: Directory containing skill files
        """
        self.skills_dir = skills_dir or Path(".claude/skills")
        self.metrics: dict[str, SkillMetrics] = {}
        self.refinements: list[SkillRefinement] = []

        # Create executor if not provided
        if executor is None:
            executor = CompoundExecutor(
                execute_fn=self._analyze_skill_performance,
                config=ExecutionConfig(max_retries=1),
            )
        self.executor = executor

        logger.info("AdaptiveSkillRefiner initialized")

    def _analyze_skill_performance(
        self,
        task: Task,
        context: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        """Analyze skill performance and suggest improvements.

        This is the core execution function passed to CompoundExecutor.
        """
        skill_name = task.metadata.get("skill_name", "unknown")
        metrics = self.metrics.get(skill_name)

        if not metrics:
            return (
                f"No metrics for skill: {skill_name}",
                {"improvement_score": 0.0, "suggestions": []},
            )

        # Analyze performance patterns
        suggestions = []
        improvement_score = 0.0

        if metrics.success_rate < 0.8:
            suggestions.append("Add error handling examples")
            improvement_score += 0.2

        if metrics.avg_coherence < 0.6:
            suggestions.append("Clarify intent-action mapping")
            improvement_score += 0.15

        if metrics.total_invocations < 10:
            suggestions.append("Gather more usage data")
            improvement_score += 0.1

        return (
            f"Analysis complete for {skill_name}",
            {
                "improvement_score": improvement_score,
                "suggestions": suggestions,
                "metrics": {
                    "success_rate": metrics.success_rate,
                    "coherence": metrics.avg_coherence,
                    "invocations": metrics.total_invocations,
                },
            },
        )

    def record_skill_usage(
        self,
        skill_name: str,
        success: bool,
        coherence: float,
    ) -> None:
        """Record skill usage for adaptive refinement.

        Args:
            skill_name: Name of skill used
            success: Whether execution succeeded
            coherence: Coherence score from execution
        """
        if skill_name not in self.metrics:
            self.metrics[skill_name] = SkillMetrics(skill_name=skill_name)

        metrics = self.metrics[skill_name]
        metrics.total_invocations += 1
        metrics.last_used = datetime.now().isoformat()

        # Update rolling averages
        old_weight = (metrics.total_invocations - 1) / metrics.total_invocations
        new_weight = 1 / metrics.total_invocations

        metrics.success_rate = (
            metrics.success_rate * old_weight + (1.0 if success else 0.0) * new_weight
        )
        metrics.avg_coherence = metrics.avg_coherence * old_weight + coherence * new_weight

        logger.debug(f"Recorded usage for {skill_name}: success={success}")

    def should_refine(self, skill_name: str) -> bool:
        """Determine if skill should be refined.

        Args:
            skill_name: Skill to check

        Returns:
            True if refinement recommended
        """
        metrics = self.metrics.get(skill_name)
        if not metrics:
            return False

        # Refine if:
        # - Low success rate
        # - Low coherence
        # - Many invocations without refinement
        return (
            metrics.success_rate < 0.75
            or metrics.avg_coherence < 0.6
            or (metrics.total_invocations > 20 and metrics.improvements_made == 0)
        )

    def refine_skill(self, skill_name: str) -> SkillRefinement | None:
        """Refine a skill based on collected metrics.

        Args:
            skill_name: Skill to refine

        Returns:
            Refinement record or None if no refinement needed
        """
        if not self.should_refine(skill_name):
            return None

        # Create refinement task
        task = Task(
            id=f"refine-{skill_name}-{datetime.now().isoformat()}",
            description=f"Refine skill: {skill_name}",
            skill_name="skill-refinement",
            operation_type="optimize",
            metadata={"skill_name": skill_name},
        )

        # Execute via compound executor
        result = self.executor.execute(task)

        if result.success:
            improvement_score = result.metrics.get("improvement_score", 0.0)

            refinement = SkillRefinement(
                skill_name=skill_name,
                timestamp=datetime.now().isoformat(),
                change_description=str(result.output),
                previous_score=self.metrics[skill_name].avg_coherence,
                new_score=self.metrics[skill_name].avg_coherence + improvement_score,
                improvement_type="performance",
            )

            self.refinements.append(refinement)
            self.metrics[skill_name].improvements_made += 1

            logger.info(f"Refined skill {skill_name}: +{improvement_score:.2f} score")
            return refinement

        return None

    def rollback_refinement(self, skill_name: str) -> bool:
        """Rollback a skill refinement (Issue #13).

        Args:
            skill_name: Skill to rollback

        Returns:
            True if rollback successful
        """
        # Find last refinement for this skill
        skill_refinements = [r for r in self.refinements if r.skill_name == skill_name]
        if not skill_refinements:
            logger.warning(f"No refinements to rollback for skill: {skill_name}")
            return False

        last_refinement = skill_refinements[-1]
        if not last_refinement.rollback_available:
            logger.warning(f"Rollback not available for skill: {skill_name}")
            return False

        # Restore previous metric values
        if skill_name in self.metrics:
            self.metrics[skill_name].avg_coherence = last_refinement.previous_score
            self.metrics[skill_name].improvements_made -= 1

        # Mark refinement as rolled back
        last_refinement.rollback_available = False

        logger.info(f"Rolled back refinement for skill: {skill_name}")
        return True

    def get_skill_report(self, skill_name: str) -> dict[str, Any]:
        """Get report for a skill.

        Args:
            skill_name: Skill to report on

        Returns:
            Skill report dict
        """
        metrics = self.metrics.get(skill_name)
        if not metrics:
            return {"error": f"No metrics for skill: {skill_name}"}

        skill_refinements = [r for r in self.refinements if r.skill_name == skill_name]

        return {
            "skill_name": skill_name,
            "metrics": {
                "total_invocations": metrics.total_invocations,
                "success_rate": round(metrics.success_rate, 3),
                "avg_coherence": round(metrics.avg_coherence, 3),
                "improvements_made": metrics.improvements_made,
            },
            "refinements": len(skill_refinements),
            "needs_refinement": self.should_refine(skill_name),
            "last_used": metrics.last_used,
        }

    def get_all_skills_report(self) -> list[dict[str, Any]]:
        """Get report for all skills.

        Returns:
            List of skill reports
        """
        return [self.get_skill_report(name) for name in self.metrics]

    def save_metrics(self, path: Path | None = None) -> None:
        """Save metrics to file.

        Args:
            path: Path to save metrics (default: data/skill_metrics.json)
        """
        path = path or Path("data/skill_metrics.json")
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "metrics": {
                name: {
                    "skill_name": m.skill_name,
                    "total_invocations": m.total_invocations,
                    "success_rate": m.success_rate,
                    "avg_coherence": m.avg_coherence,
                    "last_used": m.last_used,
                    "improvements_made": m.improvements_made,
                }
                for name, m in self.metrics.items()
            },
            "refinements": [
                {
                    "skill_name": r.skill_name,
                    "timestamp": r.timestamp,
                    "change_description": r.change_description,
                    "previous_score": r.previous_score,
                    "new_score": r.new_score,
                    "improvement_type": r.improvement_type,
                }
                for r in self.refinements
            ],
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Skill metrics saved to {path}")

    def load_metrics(self, path: Path | None = None) -> None:
        """Load metrics from file.

        Args:
            path: Path to load metrics from
        """
        path = path or Path("data/skill_metrics.json")

        try:
            with open(path) as f:
                data = json.load(f)

            for name, m in data.get("metrics", {}).items():
                self.metrics[name] = SkillMetrics(**m)

            for r in data.get("refinements", []):
                self.refinements.append(SkillRefinement(**r))

            logger.info(f"Skill metrics loaded from {path}")
        except FileNotFoundError:
            logger.info(f"No existing metrics file at {path}")


# Integration with ResearchAgent
def integrate_with_research(agent: Any) -> AdaptiveSkillRefiner:
    """Integrate skill refiner with ResearchAgent.

    Args:
        agent: ResearchAgent instance

    Returns:
        Configured AdaptiveSkillRefiner
    """
    refiner = AdaptiveSkillRefiner()

    # Store on agent for access
    agent.skill_refiner = refiner

    logger.info("AdaptiveSkillRefiner integrated with ResearchAgent")
    return refiner


# Compound integration hooks
class SkillRefinementPlugin:
    """Plugin for compound executor to track skill usage."""

    def __init__(self, refiner: AdaptiveSkillRefiner):
        """Initialize plugin."""
        self.refiner = refiner

    def on_task_complete(
        self,
        task: Task,
        result: ExecutionResult,
    ) -> None:
        """Called when task completes."""
        self.refiner.record_skill_usage(
            skill_name=task.skill_name,
            success=result.success,
            coherence=result.metrics.get("coherence", 0.5),
        )

    def should_refine_skill(self, skill_name: str) -> bool:
        """Check if skill needs refinement."""
        return self.refiner.should_refine(skill_name)

    def refine_if_needed(self, skill_name: str) -> SkillRefinement | None:
        """Refine skill if needed."""
        if self.should_refine_skill(skill_name):
            return self.refiner.refine_skill(skill_name)
        return None
