"""
Intelligence routing for task-aware model selection.

Attribution: Routing strategy inspired by Pilot's intelligence routing
Implementation: Original COHEZION design extending CostAwareRouter

Key Pattern from Pilot:
- Opus (premium) for planning and verification (reasoning-heavy)
- Sonnet (mid-tier) for implementation (spec-driven execution)
- Haiku (fast) for simple queries and lookups
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .cost_aware_router import (
    CostAwareRouter,
    ModelRoutingDecision,
    QueryComplexity,
)

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    """Classification of task cognitive load.

    Inspired by Pilot's intelligence routing pattern.
    """

    PLANNING = "planning"  # Opus-tier: spec design, architecture, requirement analysis
    VERIFICATION = "verification"  # Opus-tier: code review, validation, testing
    IMPLEMENTATION = "implementation"  # Sonnet-tier: code generation from specs
    QUERY = "query"  # Haiku-tier: simple lookups, explanations, summaries


@dataclass
class IntelligenceRoutingDecision:
    """Enhanced routing decision with task type awareness."""

    task_type: TaskType
    base_decision: ModelRoutingDecision
    override_model: Optional[str] = None  # If task type overrides complexity routing
    override_reason: Optional[str] = None


class TaskTypeClassifier:
    """Classify tasks by cognitive load type.

    Attribution: Inspired by Pilot's task-aware routing
    Implementation: COHEZION-native with keyword analysis
    """

    # Planning keywords
    PLANNING_KEYWORDS = {
        "design",
        "plan",
        "architecture",
        "spec",
        "requirements",
        "approach",
        "strategy",
        "structure",
        "outline",
        "organize",
    }

    # Verification keywords
    VERIFICATION_KEYWORDS = {
        "review",
        "verify",
        "validate",
        "test",
        "check",
        "audit",
        "inspect",
        "evaluate",
        "assess",
        "quality",
    }

    # Implementation keywords
    IMPLEMENTATION_KEYWORDS = {
        "implement",
        "build",
        "create",
        "write",
        "code",
        "develop",
        "generate",
        "construct",
        "execute",
        "make",
    }

    # Query keywords
    QUERY_KEYWORDS = {
        "what",
        "how",
        "why",
        "when",
        "where",
        "explain",
        "describe",
        "list",
        "show",
        "tell",
    }

    def classify(self, query: str) -> TaskType:
        """Classify task type from query.

        Args:
            query: User query string

        Returns:
            TaskType classification
        """
        query_lower = query.lower()

        # Count keyword matches for each type
        planning_score = self._count_keywords(query_lower, self.PLANNING_KEYWORDS)
        verification_score = self._count_keywords(
            query_lower, self.VERIFICATION_KEYWORDS
        )
        implementation_score = self._count_keywords(
            query_lower, self.IMPLEMENTATION_KEYWORDS
        )
        query_score = self._count_keywords(query_lower, self.QUERY_KEYWORDS)

        # Determine task type by highest score
        scores = {
            TaskType.PLANNING: planning_score,
            TaskType.VERIFICATION: verification_score,
            TaskType.IMPLEMENTATION: implementation_score,
            TaskType.QUERY: query_score,
        }

        max_score = max(scores.values())
        if max_score == 0:
            # Default to query for unknown patterns
            return TaskType.QUERY

        # Return task type with highest score
        return max(scores.items(), key=lambda x: x[1])[0]

    def _count_keywords(self, text: str, keywords: set[str]) -> int:
        """Count keyword matches in text."""
        return sum(
            1
            for kw in keywords
            if f" {kw} " in f" {text} "
            or text.startswith(f"{kw} ")
            or text.endswith(f" {kw}")
        )


class IntelligenceRouter:
    """Enhanced router with task-type awareness.

    Attribution: Routing pattern inspired by Pilot
    Implementation: COHEZION-native, extends CostAwareRouter

    Routing strategy:
    - Planning/Verification → Premium model (deepseek-r1)
    - Implementation with specs → Mid-tier (qwen3-coder)
    - Simple queries → Economy (phi3:mini)
    """

    # Model tier mapping for task types
    TASK_MODEL_OVERRIDE = {
        TaskType.PLANNING: "deepseek-r1:70b",  # Premium reasoning
        TaskType.VERIFICATION: "deepseek-r1:70b",  # Premium analysis
        # Implementation uses complexity-based routing (no override)
        TaskType.QUERY: "phi3:mini",  # Economy for simple lookups
    }

    def __init__(
        self,
        cost_router: Optional[CostAwareRouter] = None,
        enable_override: bool = True,
    ) -> None:
        """Initialize intelligence router.

        Args:
            cost_router: Base cost-aware router (defaults to singleton)
            enable_override: If True, task type can override complexity routing
        """
        self.cost_router = cost_router or CostAwareRouter.get_default()
        self.task_classifier = TaskTypeClassifier()
        self.enable_override = enable_override

        self._routing_history: list[IntelligenceRoutingDecision] = []

    def route(
        self,
        query: str,
        max_cost_usd: Optional[float] = None,
        force_task_type: Optional[TaskType] = None,
    ) -> IntelligenceRoutingDecision:
        """Route query with task-type awareness.

        Args:
            query: User query string
            max_cost_usd: Optional cost constraint
            force_task_type: Override task type classification

        Returns:
            IntelligenceRoutingDecision with model selection
        """
        # Classify task type
        task_type = force_task_type or self.task_classifier.classify(query)

        # Get base routing decision from complexity analysis
        base_decision, can_proceed = self.cost_router.select_model(
            query=query, max_cost_usd=max_cost_usd
        )

        # Check if task type should override complexity routing
        override_model = None
        override_reason = None

        if self.enable_override and task_type in self.TASK_MODEL_OVERRIDE:
            suggested_model = self.TASK_MODEL_OVERRIDE[task_type]

            # Only override if suggested model is different from base
            if suggested_model != base_decision.model:
                override_model = suggested_model
                override_reason = (
                    f"Task type {task_type.value} suggests {suggested_model} "
                    f"(base complexity suggested {base_decision.model})"
                )

                logger.info(
                    "Intelligence routing override: %s → %s (task type: %s)",
                    base_decision.model,
                    override_model,
                    task_type.value,
                )

        decision = IntelligenceRoutingDecision(
            task_type=task_type,
            base_decision=base_decision,
            override_model=override_model,
            override_reason=override_reason,
        )

        self._routing_history.append(decision)
        return decision

    def get_final_model(self, decision: IntelligenceRoutingDecision) -> str:
        """Get final model selection from decision.

        Args:
            decision: Routing decision

        Returns:
            Model name to use
        """
        return decision.override_model or decision.base_decision.model

    def get_routing_stats(self) -> dict:
        """Get routing statistics.

        Returns:
            Dictionary with routing analytics
        """
        if not self._routing_history:
            return {}

        total = len(self._routing_history)
        overrides = sum(1 for d in self._routing_history if d.override_model)

        task_counts = {}
        for task_type in TaskType:
            task_counts[task_type.value] = sum(
                1 for d in self._routing_history if d.task_type == task_type
            )

        return {
            "total_routes": total,
            "overrides": overrides,
            "override_rate": overrides / total if total > 0 else 0.0,
            "task_type_distribution": task_counts,
        }
