"""Elegant simplified skill selection.

Replaces skill_selector.py (418 lines) + skill_consensus_voter.py (560 lines)
+ skill_refiner.py (383 lines) with clean unified implementation.
Total: 1,361 lines → ~150 lines
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from cohezion.compound.models import ExecutionResult, Task


logger = logging.getLogger(__name__)


@dataclass
class SkillMatch:
    """Match between task and skill."""

    skill_name: str
    confidence: float
    relevance_score: float

    def __gt__(self, other: SkillMatch) -> bool:
        return self.confidence > other.confidence


class SkillSelector:
    """Unified skill selection.

    Clean implementation vs complex voting/refinement systems.
    """

    def __init__(
        self,
        skill_registry: dict[str, Callable] | None = None,
        scorer: Callable[[Task, str], float] | None = None,
    ):
        self.skill_registry = skill_registry or {}
        self.scorer = scorer or self._default_scorer

    def select(self, task: Task, top_k: int = 3) -> list[SkillMatch]:
        """Select best skills for task.

        Simple scoring vs complex consensus voting.
        """
        if not self.skill_registry:
            logger.warning("No skills registered")
            return []

        matches = []
        for skill_name in self.skill_registry.keys():
            confidence = self.scorer(task, skill_name)
            if confidence > 0.3:  # Minimum threshold
                matches.append(
                    SkillMatch(
                        skill_name=skill_name,
                        confidence=confidence,
                        relevance_score=confidence,
                    )
                )

        # Sort by confidence
        matches.sort(reverse=True)

        return matches[:top_k]

    def select_best(self, task: Task) -> SkillMatch | None:
        """Select single best skill."""
        matches = self.select(task, top_k=1)
        return matches[0] if matches else None

    def _default_scorer(self, task: Task, skill_name: str) -> float:
        """Default scoring based on skill name matching."""
        # Simple string similarity
        task_lower = task.skill_name.lower()
        skill_lower = skill_name.lower()

        if task_lower == skill_lower:
            return 1.0
        if task_lower in skill_lower or skill_lower in task_lower:
            return 0.8

        # Word overlap
        task_words = set(task_lower.split("_"))
        skill_words = set(skill_lower.split("_"))
        overlap = len(task_words & skill_words)
        total = len(task_words | skill_words)

        return overlap / total if total > 0 else 0.0

    def register_skill(self, name: str, handler: Callable) -> None:
        """Register a skill."""
        self.skill_registry[name] = handler
        logger.info(f"Registered skill: {name}")

    def get_skill(self, name: str) -> Callable | None:
        """Get skill handler by name."""
        return self.skill_registry.get(name)


class SkillRefiner:
    """Simple skill refinement based on feedback."""

    def __init__(self, selector: SkillSelector):
        self.selector = selector
        self.feedback_history: list[tuple[Task, ExecutionResult]] = []

    def record_feedback(self, task: Task, result: ExecutionResult) -> None:
        """Record execution feedback."""
        self.feedback_history.append((task, result))

        # Keep history bounded
        if len(self.feedback_history) > 100:
            self.feedback_history = self.feedback_history[-50:]

    def suggest_refinement(self, skill_name: str) -> dict[str, float]:
        """Suggest skill refinements based on success patterns."""
        # Find successful uses of this skill
        successes = [
            (task, result) for task, result in self.feedback_history if task.skill_name == skill_name and result.success
        ]

        failures = [
            (task, result)
            for task, result in self.feedback_history
            if task.skill_name == skill_name and not result.success
        ]

        if not successes and not failures:
            return {}

        # Calculate success rate
        total = len(successes) + len(failures)
        success_rate = len(successes) / total if total > 0 else 0.0

        return {
            "skill_name": skill_name,
            "success_rate": success_rate,
            "total_executions": total,
            "recommendation": ("improve" if success_rate < 0.7 else "maintain"),
        }


class SimpleSkills:
    """Minimal skill selection for basic use cases."""

    def __init__(self, skills: dict[str, Callable]):
        self.skills = skills

    def execute(self, task: Task) -> ExecutionResult:
        """Execute task with matching skill."""
        handler = self.skills.get(task.skill_name)

        if not handler:
            return ExecutionResult(
                success=False,
                output=f"Unknown skill: {task.skill_name}",
                error_type="SkillNotFound",
            )

        try:
            output = handler(task.description, task.context)
            return ExecutionResult(
                success=True,
                output=str(output),
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                output=str(e),
                error_type=type(e).__name__,
            )
