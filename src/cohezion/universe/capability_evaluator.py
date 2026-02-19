"""RL Capability Evaluator - Multi-Dimensional Agent Assessment.

Evaluates agent navigation capability in morphospace across 6 dimensions:
task_completion, coherence_maintenance, context_retention, ambiguity_handling,
interruption_recovery, judgment_quality.

Designed to be extensible to LLM agents - dimension names map to higher-order
capabilities when the agent substrate changes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from cohezion.universe.scenarios import Scenario, ScenarioType


logger = logging.getLogger(__name__)

# HIHO target coherence
HIHO_TARGET = 0.5


@dataclass
class CapabilityScore:
    """Multi-dimensional capability score for an agent journey."""

    task_completion: float  # Did agent reach target/goal? (0.0-1.0)
    coherence_maintenance: float  # Maintained HIHO stability? (0.0-1.0)
    context_retention: float  # Showed awareness of prior steps? (0.0-1.0)
    ambiguity_handling: float  # Navigated uncertain target wells? (0.0-1.0)
    interruption_recovery: float  # Recovered after context switches? (0.0-1.0)
    judgment_quality: float  # Selected optimal among competing objectives? (0.0-1.0)

    def composite(self) -> float:
        """Compute weighted average composite score.

        Returns:
            Composite score (0.0-1.0)
        """
        # Equal weights for now
        scores = [
            self.task_completion,
            self.coherence_maintenance,
            self.context_retention,
            self.ambiguity_handling,
            self.interruption_recovery,
            self.judgment_quality,
        ]
        return sum(scores) / len(scores)


@dataclass
class CapabilityProfile:
    """Aggregate capability profile across multiple scenarios."""

    task_completion: float
    coherence_maintenance: float
    context_retention: float
    ambiguity_handling: float
    interruption_recovery: float
    judgment_quality: float
    num_scenarios: int

    @classmethod
    def from_scores(cls, scores: list[CapabilityScore]) -> CapabilityProfile:
        """Aggregate scores across scenarios.

        Args:
            scores: List of CapabilityScore from different scenarios

        Returns:
            CapabilityProfile with mean scores
        """
        if not scores:
            return cls(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0)

        return cls(
            task_completion=sum(s.task_completion for s in scores) / len(scores),
            coherence_maintenance=sum(s.coherence_maintenance for s in scores)
            / len(scores),
            context_retention=sum(s.context_retention for s in scores) / len(scores),
            ambiguity_handling=sum(s.ambiguity_handling for s in scores) / len(scores),
            interruption_recovery=sum(s.interruption_recovery for s in scores)
            / len(scores),
            judgment_quality=sum(s.judgment_quality for s in scores) / len(scores),
            num_scenarios=len(scores),
        )


class CapabilityEvaluator:
    """Evaluate agent capability across multiple dimensions."""

    def evaluate(
        self, scenario: Scenario, journey: list[dict[str, float]]
    ) -> CapabilityScore:
        """Evaluate agent journey for a scenario.

        Args:
            scenario: Scenario definition
            journey: Agent's trajectory (list of state dicts)

        Returns:
            CapabilityScore across all dimensions
        """
        # Call scenario's reward function for task completion
        task_completion = scenario.reward_function(journey) if journey else 0.0

        # Evaluate coherence maintenance (HIHO stability)
        coherence_maintenance = self._evaluate_coherence(journey)

        # Evaluate context retention (path efficiency, no revisiting)
        context_retention = self._evaluate_context_retention(journey)

        # Evaluate ambiguity handling (scenario-specific)
        ambiguity_handling = self._evaluate_ambiguity(scenario, journey)

        # Evaluate interruption recovery (scenario-specific)
        interruption_recovery = self._evaluate_interruption_recovery(scenario, journey)

        # Evaluate judgment quality (scenario-specific)
        judgment_quality = self._evaluate_judgment(scenario, journey)

        # Anti-gaming checks
        if self._is_degenerate_strategy(journey):
            # Penalize zero exploration / constant action
            task_completion *= 0.5
            context_retention *= 0.5

        return CapabilityScore(
            task_completion=task_completion,
            coherence_maintenance=coherence_maintenance,
            context_retention=context_retention,
            ambiguity_handling=ambiguity_handling,
            interruption_recovery=interruption_recovery,
            judgment_quality=judgment_quality,
        )

    def _evaluate_coherence(self, journey: list[dict[str, float]]) -> float:
        """Evaluate coherence maintenance (HIHO stability at 0.5).

        Args:
            journey: Agent trajectory

        Returns:
            Coherence score (0.0-1.0)
        """
        if not journey:
            return 0.0

        coherence_values = [point.get("coherence", 0.5) for point in journey]
        # Reward = 1.0 - avg_deviation_from_HIHO_target
        avg_deviation = sum(abs(c - HIHO_TARGET) for c in coherence_values) / len(
            coherence_values
        )
        # Scale: 0.5 deviation = 0 score, 0 deviation = 1.0 score
        return max(0.0, 1.0 - avg_deviation * 2.0)

    def _evaluate_context_retention(self, journey: list[dict[str, float]]) -> float:
        """Evaluate context retention (path efficiency, not revisiting states).

        Args:
            journey: Agent trajectory

        Returns:
            Context retention score (0.0-1.0)
        """
        if len(journey) < 2:
            return 0.5  # Neutral for very short journeys

        # Measure path efficiency: total distance traveled vs direct distance
        positions = [(point.get("x", 0.0), point.get("y", 0.0)) for point in journey]

        # Total path length
        total_distance = sum(
            np.linalg.norm(np.array(positions[i + 1]) - np.array(positions[i]))
            for i in range(len(positions) - 1)
        )

        # Direct distance (start to end)
        direct_distance = np.linalg.norm(
            np.array(positions[-1]) - np.array(positions[0])
        )

        if total_distance == 0:
            return 0.0  # No movement

        # Efficiency: direct / total (1.0 = perfectly straight path)
        efficiency = direct_distance / total_distance if total_distance > 0 else 0.0

        return float(min(1.0, efficiency))

    def _evaluate_ambiguity(
        self, scenario: Scenario, journey: list[dict[str, float]]
    ) -> float:
        """Evaluate ambiguity handling (scenario-specific).

        Args:
            scenario: Scenario with ambiguity level
            journey: Agent trajectory

        Returns:
            Ambiguity handling score (0.0-1.0)
        """
        # For now, use task completion scaled by ambiguity difficulty
        # Higher ambiguity = more impressive completion
        if scenario.difficulty.ambiguity_level > 0:
            return scenario.reward_function(journey) * (
                1.0 + scenario.difficulty.ambiguity_level
            )
        return 0.5  # Neutral for non-ambiguous scenarios

    def _evaluate_interruption_recovery(
        self, scenario: Scenario, journey: list[dict[str, float]]
    ) -> float:
        """Evaluate interruption recovery (context switch handling).

        Args:
            scenario: Scenario with interruption points
            journey: Agent trajectory

        Returns:
            Interruption recovery score (0.0-1.0)
        """
        if scenario.type != ScenarioType.INTERRUPTION:
            return 0.5  # Neutral for non-interruption scenarios

        interruptions = scenario.interruptions
        if not interruptions:
            return 0.5

        # Measure recovery time after each interruption
        recovery_scores = []
        for interruption in interruptions:
            interrupt_step_val = interruption.get("step", 0)
            interrupt_step = (
                int(interrupt_step_val)
                if isinstance(interrupt_step_val, (int, float))
                else 0
            )

            if interrupt_step >= len(journey):
                continue

            # Look at next few steps after interruption
            window_size = min(scenario.difficulty.context_depth, 5)
            post_interrupt = journey[
                interrupt_step : min(interrupt_step + window_size, len(journey))
            ]

            if not post_interrupt:
                recovery_scores.append(0.0)
                continue

            # Distance from target at end of recovery window
            final_pos = post_interrupt[-1]
            target_x = scenario.target_state.get("x", 0.0)
            target_y = scenario.target_state.get("y", 0.0)
            distance = np.linalg.norm(
                np.array([final_pos.get("x", 0.0), final_pos.get("y", 0.0)])
                - np.array([target_x, target_y])
            )

            # Recovery score: closer = better
            recovery_score = max(0.0, 1.0 - distance / 2.0)
            recovery_scores.append(recovery_score)

        return sum(recovery_scores) / len(recovery_scores) if recovery_scores else 0.0

    def _evaluate_judgment(
        self, scenario: Scenario, journey: list[dict[str, float]]
    ) -> float:
        """Evaluate judgment quality (choosing optimal among competing objectives).

        Args:
            scenario: Scenario with competing objectives
            journey: Agent trajectory

        Returns:
            Judgment quality score (0.0-1.0)
        """
        if scenario.type != ScenarioType.JUDGMENT:
            return 0.5  # Neutral for non-judgment scenarios

        if not scenario.competing_objectives:
            return 0.5

        # Use scenario reward function (already checks if optimal was chosen)
        return scenario.reward_function(journey)

    def _is_degenerate_strategy(self, journey: list[dict[str, float]]) -> bool:
        """Detect degenerate strategies (constant action, zero exploration).

        Args:
            journey: Agent trajectory

        Returns:
            True if degenerate strategy detected
        """
        if len(journey) < 3:
            return False

        # Check for constant position (no movement)
        positions = [(point.get("x", 0.0), point.get("y", 0.0)) for point in journey]
        total_movement = sum(
            np.linalg.norm(np.array(positions[i + 1]) - np.array(positions[i]))
            for i in range(len(positions) - 1)
        )

        # If total movement is very small, it's degenerate
        return bool(total_movement < 0.01 * len(journey))
