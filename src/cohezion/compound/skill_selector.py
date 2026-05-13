"""Experience-guided skill selection using vault performance patterns.

Analyzes vault patterns to find skills that performed best on similar tasks.
Uses metrics like coherence and token efficiency to rank candidate skills.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any

from cohezion.core.mcp_client import MCPClient


logger = logging.getLogger(__name__)


@dataclass
class SkillScore:
    """Performance score for a skill candidate."""

    skill_name: str
    coherence_score: float  # 0.0-1.0
    token_efficiency: float  # 0.0-1.0
    success_rate: float  # 0.0-1.0
    times_used: int  # Number of successful uses
    composite_score: float  # Weighted combination

    def __lt__(self, other: "SkillScore") -> bool:
        """Comparison for sorting (higher scores first)."""
        return self.composite_score > other.composite_score

    def __repr__(self) -> str:
        """Readable representation."""
        return (
            f"SkillScore(skill={self.skill_name}, "
            f"composite={self.composite_score:.3f}, "
            f"coherence={self.coherence_score:.2f}, "
            f"efficiency={self.token_efficiency:.2f})"
        )


class SkillSelector:
    """Experience-guided skill selection from vault patterns.

    Queries the vault for performance patterns of skills on similar tasks
    and selects the best-performing skill based on coherence and efficiency.

    Example:
        ```python
        selector = SkillSelector(mcp_client)

        # Find best skill for a task
        best_skills = selector.select_skills(
            task_description="Generate 10 creative story ideas",
            operation_type="generate",
            top_k=3
        )

        for skill_score in best_skills:
            print(f"Try {skill_score.skill_name}: "
                  f"coherence={skill_score.coherence_score:.2f}, "
                  f"efficiency={skill_score.token_efficiency:.2f}")
        ```
    """

    def __init__(
        self,
        mcp_client: MCPClient,
        coherence_weight: float = 0.5,
        efficiency_weight: float = 0.3,
        success_weight: float = 0.2,
    ):
        """Initialize skill selector.

        Args:
            mcp_client: Connected MCPClient for vault queries
            coherence_weight: Weight for coherence score (0.0-1.0)
            efficiency_weight: Weight for token efficiency (0.0-1.0)
            success_weight: Weight for success rate (0.0-1.0)
        """
        self.mcp_client = mcp_client
        self.coherence_weight = coherence_weight
        self.efficiency_weight = efficiency_weight
        self.success_weight = success_weight

        # Normalize weights
        total = coherence_weight + efficiency_weight + success_weight
        self.coherence_weight /= total
        self.efficiency_weight /= total
        self.success_weight /= total

        logger.debug(
            "Initialized SkillSelector with weights: coherence=%.2f, efficiency=%.2f, success=%.2f",
            self.coherence_weight,
            self.efficiency_weight,
            self.success_weight,
        )

    def select_skills(
        self,
        task_description: str,
        operation_type: str,
        project: str = "cohezion",
        top_k: int = 3,
    ) -> list[SkillScore]:
        """Select best skills for a task based on vault patterns.

        Uses fast hierarchical search when available (5-10× faster than full-text).

        Args:
            task_description: Description of the task
            operation_type: Type of operation (generate, analyze, search, etc.)
            project: Project name for scoped search
            top_k: Number of top skills to return

        Returns:
            List of SkillScore objects, sorted by composite score (highest first)

        Performance:
            Hierarchical search: 5-10ms per query (5-10× faster than full-text)
        """
        logger.info(
            "Selecting skills for task: %s (operation=%s)",
            task_description[:100],
            operation_type,
        )

        try:
            # Query vault for relevant patterns
            context = self.mcp_client.vault_find_relevant_context(
                query=f"{task_description} {operation_type}",
                project=project,
            )

            # Extract skill performance data from patterns
            skill_scores = self._extract_skill_scores(context, operation_type)

            # Sort by composite score
            skill_scores.sort()

            # Return top-k
            result = skill_scores[:top_k]
            logger.info(
                "Selected %d skills: %s",
                len(result),
                ", ".join(s.skill_name for s in result),
            )
            return result

        except Exception as e:
            logger.warning(
                "Error selecting skills: %s. Returning empty list.",
                e,
                exc_info=True,
            )
            return []

    def _extract_skill_scores(self, context: Any, operation_type: str) -> list[SkillScore]:
        """Extract skill performance scores from vault context.

        Args:
            context: Context returned from vault_find_relevant_context
            operation_type: Type of operation

        Returns:
            List of SkillScore objects
        """
        skill_scores = {}

        # Parse context if it's a dict
        if isinstance(context, dict):
            patterns = context.get("patterns", [])
        else:
            patterns = context if isinstance(context, list) else []

        for pattern in patterns:
            # Extract skill name and metrics from pattern
            if isinstance(pattern, dict):
                skill_data = self._parse_pattern_dict(pattern, operation_type)
            else:
                skill_data = self._parse_pattern_string(str(pattern), operation_type)

            if skill_data:
                skill_name = skill_data["skill_name"]
                if skill_name not in skill_scores:
                    skill_scores[skill_name] = {
                        "coherence": [],
                        "efficiency": [],
                        "success": [],
                        "count": 0,
                    }

                # Accumulate metrics
                if "coherence" in skill_data:
                    skill_scores[skill_name]["coherence"].append(skill_data["coherence"])
                if "efficiency" in skill_data:
                    skill_scores[skill_name]["efficiency"].append(skill_data["efficiency"])
                if "success" in skill_data:
                    skill_scores[skill_name]["success"].append(skill_data["success"])
                skill_scores[skill_name]["count"] += 1

        # Aggregate metrics and compute composite scores
        result = []
        for skill_name, metrics in skill_scores.items():
            # Average the metrics
            coherence = sum(metrics["coherence"]) / len(metrics["coherence"]) if metrics["coherence"] else 0.5
            efficiency = sum(metrics["efficiency"]) / len(metrics["efficiency"]) if metrics["efficiency"] else 0.5
            success = sum(metrics["success"]) / len(metrics["success"]) if metrics["success"] else 0.5

            # Compute composite score
            composite = (
                self.coherence_weight * coherence + self.efficiency_weight * efficiency + self.success_weight * success
            )

            score = SkillScore(
                skill_name=skill_name,
                coherence_score=coherence,
                token_efficiency=efficiency,
                success_rate=success,
                times_used=metrics["count"],
                composite_score=composite,
            )
            result.append(score)

        logger.debug("Extracted %d unique skills from patterns", len(result))
        return result

    def _parse_pattern_dict(self, pattern: dict, operation_type: str) -> dict | None:
        """Parse skill data from pattern dictionary.

        Args:
            pattern: Pattern dictionary
            operation_type: Expected operation type

        Returns:
            Dictionary with skill_name, coherence, efficiency, success
        """
        # Look for skill identification in pattern
        # Patterns may have structure like: {source: "experiment", title: "...", ...}
        title = pattern.get("title", "")
        content = pattern.get("content", "")

        # Try to extract skill name from title/content
        # Expected patterns: "skill_name_operation_type_success"
        # or "Skill Name" or mentions in content
        skill_name = self._extract_skill_name(title) or self._extract_skill_name(content)

        if not skill_name:
            return None

        # Extract metrics from pattern
        metrics = self._extract_metrics(content)

        return {
            "skill_name": skill_name,
            "coherence": metrics.get("coherence", 0.5),
            "efficiency": metrics.get("efficiency", 0.5),
            "success": 1.0 if "success" in title.lower() else metrics.get("success", 0.5),
        }

    def _parse_pattern_string(self, pattern_str: str, operation_type: str) -> dict | None:
        """Parse skill data from pattern string.

        Args:
            pattern_str: Pattern as string
            operation_type: Expected operation type

        Returns:
            Dictionary with skill_name, coherence, efficiency, success
        """
        # Try to extract skill name from string
        skill_name = self._extract_skill_name(pattern_str)

        if not skill_name:
            return None

        # Extract metrics from string
        metrics = self._extract_metrics(pattern_str)

        return {
            "skill_name": skill_name,
            "coherence": metrics.get("coherence", 0.5),
            "efficiency": metrics.get("efficiency", 0.5),
            "success": metrics.get("success", 0.5),
        }

    def _extract_skill_name(self, text: str) -> str | None:
        """Extract skill name from text.

        Looks for patterns like:
        - "skill_name_operation_success"
        - "Skill Name:" mentions
        - Direct skill references

        Args:
            text: Text to search

        Returns:
            Extracted skill name or None
        """
        if not text:
            return None

        # Pattern 1: skill_name_operation_type in filename/title
        match = re.search(r"(\w+)_(generate|analyze|search|transform|persist)", text)
        if match:
            return match.group(1)

        # Pattern 2: "skill:" or "Skill:" followed by name
        match = re.search(r"[Ss]kill[:\s]+(\w+)", text)
        if match:
            return match.group(1)

        # Pattern 3: skill name as first word-like token
        match = re.search(r"^(\w+)", text.strip())
        if match:
            token = match.group(1)
            if token not in ["the", "a", "an", "this", "that", "for", "with"]:
                return token

        return None

    def _extract_metrics(self, text: str) -> dict[str, float]:
        """Extract performance metrics from text.

        Looks for patterns like:
        - "coherence: 0.85" or "coherence=0.85"
        - "efficiency: 0.75" or "efficiency=0.75"
        - "success_rate: 0.9" or "success=0.9"

        Args:
            text: Text to search

        Returns:
            Dictionary with extracted metrics (0.0-1.0)
        """
        metrics = {}

        # Coherence
        match = re.search(r"coherence[:\s=]+(\d+\.?\d*)", text, re.IGNORECASE)
        if match:
            metrics["coherence"] = float(match.group(1))

        # Efficiency
        match = re.search(r"efficiency[:\s=]+(\d+\.?\d*)", text, re.IGNORECASE)
        if match:
            metrics["efficiency"] = float(match.group(1))

        # Success rate
        match = re.search(r"success(?:_rate)?[:\s=]+(\d+\.?\d*)", text, re.IGNORECASE)
        if match:
            metrics["success"] = float(match.group(1))

        # Ensure metrics are in range [0.0, 1.0]
        for key, value in metrics.items():
            if value > 1.0:
                # Assume percentage
                metrics[key] = value / 100.0
            metrics[key] = max(0.0, min(1.0, metrics[key]))

        return metrics

    def rank_skills(
        self,
        available_skills: list[str],
        task_description: str,
        operation_type: str,
        project: str = "cohezion",
    ) -> list[tuple[str, float]]:
        """Rank available skills for a task.

        Args:
            available_skills: List of skill names to rank
            task_description: Description of the task
            operation_type: Type of operation
            project: Project name

        Returns:
            List of (skill_name, score) tuples, sorted by score (highest first)
        """
        # Get vault-based selections
        vault_selections = self.select_skills(
            task_description,
            operation_type,
            project,
            top_k=len(available_skills),
        )

        vault_skills_by_name = {s.skill_name: s for s in vault_selections}

        # Rank available skills
        ranked = []
        for skill_name in available_skills:
            if skill_name in vault_skills_by_name:
                score = vault_skills_by_name[skill_name].composite_score
            else:
                # Fallback: give low but reasonable score to unranked skills
                score = 0.3
                logger.debug("Skill %s not found in vault patterns", skill_name)

            ranked.append((skill_name, score))

        # Sort by score (highest first)
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked
