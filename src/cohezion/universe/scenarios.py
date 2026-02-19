"""Agentic Scenario Generation for Training Environments.

Generates training scenarios requiring agents to navigate ambiguity, handle
interruptions, maintain context over extended interactions, and exercise judgment.
Aligned with Anthropic's Universes team evaluation framework.
"""

from __future__ import annotations

import logging
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

import numpy as np


logger = logging.getLogger(__name__)


class TrajectoryPoint(Protocol):
    """Protocol for trajectory point with position/state info."""

    def get(self, key: str, default: float = 0.0) -> float: ...


class ScenarioType(str, Enum):
    """Types of training scenarios."""

    NAVIGATION = "navigation"  # Find target in morphospace
    MAINTENANCE = "maintenance"  # Keep coherence under perturbation
    JUDGMENT = "judgment"  # Choose between competing objectives
    INTERRUPTION = "interruption"  # Resume after context switch


@dataclass
class ScenarioDifficulty:
    """Configurable difficulty parameters for scenarios."""

    ambiguity_level: float = 0.5  # 0.0-1.0: How unclear goal/instructions are
    interruption_count: int = 0  # 0-N: Number of context-switching interruptions
    context_depth: int = 1  # 1-N: How many prior steps must be remembered
    judgment_complexity: float = 0.5  # 0.0-1.0: Degree of nuanced evaluation needed


@dataclass
class Scenario:
    """Training scenario definition."""

    type: ScenarioType
    difficulty: ScenarioDifficulty
    description: str
    target_state: dict[str, float]  # Goal state or target coordinates
    reward_function: Callable[
        [list[dict[str, float]]], float
    ]  # Maps trajectory to score
    interruptions: list[dict[str, float | int | bool]] = field(
        default_factory=list
    )  # Context switches
    competing_objectives: list[dict[str, float]] = field(
        default_factory=list
    )  # For judgment


class ScenarioGenerator:
    """Generate training scenarios with random perturbation."""

    rng: random.Random
    np_rng: np.random.Generator

    def __init__(self, seed: int | None = None):
        """Initialize generator with random seed for reproducibility."""
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)

    def generate(
        self,
        scenario_type: ScenarioType,
        difficulty: ScenarioDifficulty | None = None,
    ) -> Scenario:
        """Generate a scenario of the specified type with given difficulty.

        Args:
            scenario_type: Type of scenario to generate
            difficulty: Difficulty configuration, or default if None

        Returns:
            Generated Scenario instance
        """
        if difficulty is None:
            difficulty = ScenarioDifficulty()

        if scenario_type == ScenarioType.NAVIGATION:
            return self._generate_navigation(difficulty)
        elif scenario_type == ScenarioType.MAINTENANCE:
            return self._generate_maintenance(difficulty)
        elif scenario_type == ScenarioType.JUDGMENT:
            return self._generate_judgment(difficulty)
        elif scenario_type == ScenarioType.INTERRUPTION:
            return self._generate_interruption(difficulty)
        else:
            raise ValueError(f"Unknown scenario type: {scenario_type}")

    def _generate_navigation(self, difficulty: ScenarioDifficulty) -> Scenario:
        """Generate navigation scenario: find target in morphospace."""
        # Random target position with noise based on ambiguity
        noise = difficulty.ambiguity_level * self.rng.uniform(-0.2, 0.2)
        target_state = {
            "x": self.rng.uniform(-1.0, 1.0) + noise,
            "y": self.rng.uniform(-1.0, 1.0) + noise,
            "z": self.rng.uniform(-1.0, 1.0) + noise,
        }

        def reward_function(trajectory: list[dict[str, float]]) -> float:
            """Reward based on proximity to target at end of trajectory."""
            if not trajectory:
                return 0.0
            # Assume trajectory contains dicts with x, y, z keys
            final_pos = trajectory[-1] if trajectory else {"x": 0.0, "y": 0.0, "z": 0.0}
            distance = (
                sum(
                    (final_pos.get(k, 0.0) - target_state.get(k, 0.0)) ** 2
                    for k in ["x", "y", "z"]
                )
                ** 0.5
            )
            # Inverse distance reward (1.0 = at target, 0.0 = far away)
            return max(0.0, 1.0 - distance / 3.0)  # Normalize by max distance ~3.0

        return Scenario(
            type=ScenarioType.NAVIGATION,
            difficulty=difficulty,
            description=f"Navigate to target position {target_state} in morphospace",
            target_state=target_state,
            reward_function=reward_function,
        )

    def _generate_maintenance(self, difficulty: ScenarioDifficulty) -> Scenario:
        """Generate maintenance scenario: maintain coherence under perturbation."""
        # Target HIHO coherence = 0.5
        target_coherence = 0.5
        perturbation_strength = difficulty.ambiguity_level * 0.3

        def reward_function(trajectory: list[dict[str, float]]) -> float:
            """Reward based on coherence stability."""
            if not trajectory:
                return 0.0
            # Assume trajectory contains dicts with "coherence" key
            coherence_values = [point.get("coherence", 0.5) for point in trajectory]
            # Reward = 1.0 - avg_deviation_from_target
            avg_deviation = sum(
                abs(c - target_coherence) for c in coherence_values
            ) / len(coherence_values)
            return max(0.0, 1.0 - avg_deviation * 2.0)  # Scale deviation

        interruptions: list[dict[str, float | int | bool]] = [
            {"step": i * 10, "strength": perturbation_strength}
            for i in range(1, difficulty.interruption_count + 1)
        ]

        return Scenario(
            type=ScenarioType.MAINTENANCE,
            difficulty=difficulty,
            description=f"Maintain HIHO coherence near {target_coherence} under {difficulty.interruption_count} perturbations",
            target_state={"coherence": target_coherence},
            reward_function=reward_function,
            interruptions=interruptions,
        )

    def _generate_judgment(self, difficulty: ScenarioDifficulty) -> Scenario:
        """Generate judgment scenario: choose between competing objectives."""
        # Multiple stability wells with trade-offs
        num_wells = max(2, int(difficulty.judgment_complexity * 5))

        # Store wells as flat dicts with x, y, quality
        competing_wells: list[dict[str, float]] = [
            {
                "id": float(i),
                "x": self.rng.uniform(-1.0, 1.0),
                "y": self.rng.uniform(-1.0, 1.0),
                "quality": self.rng.uniform(0.5, 1.0),
            }
            for i in range(num_wells)
        ]

        # Best objective (highest quality)
        best_well = max(competing_wells, key=lambda obj: obj["quality"])

        def reward_function(trajectory: list[dict[str, float]]) -> float:
            """Reward based on selection of optimal objective."""
            if not trajectory:
                return 0.0
            # Assume trajectory contains path toward one objective
            final_pos = trajectory[-1] if trajectory else {"x": 0.0, "y": 0.0}
            # Find which objective agent is closest to
            distances = [
                sum((final_pos.get(k, 0.0) - well.get(k, 0.0)) ** 2 for k in ["x", "y"])
                ** 0.5
                for well in competing_wells
            ]
            closest_idx = distances.index(min(distances))
            # Reward if chose best objective
            chosen_quality = competing_wells[closest_idx]["quality"]
            return (
                chosen_quality
                if closest_idx == competing_wells.index(best_well)
                else 0.3
            )

        return Scenario(
            type=ScenarioType.JUDGMENT,
            difficulty=difficulty,
            description=f"Choose optimal objective among {num_wells} competing stability wells",
            target_state={
                "x": best_well["x"],
                "y": best_well["y"],
                "quality": best_well["quality"],
            },
            reward_function=reward_function,
            competing_objectives=[well for well in competing_wells],
        )

    def _generate_interruption(self, difficulty: ScenarioDifficulty) -> Scenario:
        """Generate interruption scenario: resume after context switches."""
        # Target to reach before/after interruptions
        target_state = {
            "x": self.rng.uniform(-0.5, 0.5),
            "y": self.rng.uniform(-0.5, 0.5),
        }

        # Interruptions that force context switch
        interruptions: list[dict[str, float | int | bool]] = [
            {
                "step": i * 5,
                "context_reset": True,
                "forced_state_x": self.rng.uniform(-1.0, 1.0),
                "forced_state_y": self.rng.uniform(-1.0, 1.0),
            }
            for i in range(1, difficulty.interruption_count + 1)
        ]

        def reward_function(trajectory: list[dict[str, float]]) -> float:
            """Reward based on recovery speed after interruptions."""
            if not trajectory:
                return 0.0
            # Measure how quickly agent re-orients to target after each interruption
            recovery_scores: list[float] = []
            for interruption in interruptions:
                interrupt_step_val = interruption.get("step", 0)
                interrupt_step = (
                    int(interrupt_step_val)
                    if isinstance(interrupt_step_val, (int, float))
                    else 0
                )
                if interrupt_step >= len(trajectory):
                    continue
                # Look at next N steps after interruption
                post_interrupt_steps = trajectory[
                    interrupt_step : min(
                        interrupt_step + difficulty.context_depth, len(trajectory)
                    )
                ]
                if not post_interrupt_steps:
                    recovery_scores.append(0.0)
                    continue
                # Distance from target at end of recovery window
                final_pos = post_interrupt_steps[-1]
                distance = (
                    sum(
                        (final_pos.get(k, 0.0) - target_state.get(k, 0.0)) ** 2
                        for k in ["x", "y"]
                    )
                    ** 0.5
                )
                recovery_score = max(0.0, 1.0 - distance / 2.0)
                recovery_scores.append(recovery_score)

            return (
                sum(recovery_scores) / len(recovery_scores) if recovery_scores else 0.0
            )

        return Scenario(
            type=ScenarioType.INTERRUPTION,
            difficulty=difficulty,
            description=f"Resume navigation to target after {difficulty.interruption_count} context switches",
            target_state=target_state,
            reward_function=reward_function,
            interruptions=interruptions,
        )
