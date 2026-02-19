"""Bioelectric Scenario Navigator - Gradient-Based Agent Navigation.

Integrates Levin's bioelectric navigation into scenario execution pipeline,
using BioelectricEngine for gradient-based action guidance in morphospace.
"""

from __future__ import annotations

import logging

import numpy as np

from cohezion.flume.bioelectric import BioelectricEngine
from cohezion.universe.evo_agent import EVOAgent
from cohezion.universe.scenarios import Scenario, ScenarioType


logger = logging.getLogger(__name__)


class BioelectricNavigator:
    """Navigate agents through scenarios using bioelectric signals."""

    def __init__(self, engine: BioelectricEngine | None = None):
        """Initialize navigator.

        Args:
            engine: BioelectricEngine instance (default: creates new one)
        """
        self.engine = engine or BioelectricEngine()

    def navigate_scenario(
        self,
        scenario: Scenario,
        agent: EVOAgent,
        max_steps: int = 50,
        step_size: float = 0.1,
    ) -> list[dict[str, np.ndarray | str]]:
        """Navigate agent through scenario using bioelectric guidance.

        Args:
            scenario: Scenario to execute
            agent: EVO agent to navigate
            max_steps: Maximum number of steps
            step_size: Step size for each move

        Returns:
            Trajectory as list of dicts with state, signal, action
        """
        # Extract target from scenario
        target = self._extract_target(scenario)

        # Validate morphospace if judgment scenario
        if scenario.type == ScenarioType.JUDGMENT:
            target = self._validate_morphospace(scenario, target)

        # Apply ambiguity noise if present
        if scenario.difficulty.ambiguity_level > 0:
            target = self._add_ambiguity_noise(
                target, scenario.difficulty.ambiguity_level
            )

        trajectory = []

        for step in range(max_steps):
            # Check for interruptions
            if self._should_interrupt(scenario, step):
                self._apply_interruption(scenario, agent, step)

            # Get current state as numpy
            current_state = agent.to_numpy()

            # Bioelectric step toward target
            new_state, action = self.engine.step(current_state, target, step_size)

            # Get bioelectric signal for logging
            signal = self.engine.encode_signal(current_state, target)

            # Update agent state
            agent.update_from_numpy(new_state)

            # Record trajectory point
            trajectory.append(
                {
                    "state": new_state,
                    "signal": {
                        "voltage": signal.voltage,
                        "intensity": signal.intensity,
                        "pattern": signal.pattern,
                    },
                    "action": {
                        "direction": action.direction,
                        "magnitude": action.magnitude,
                    },
                }
            )

            # Check if reached target
            if self._reached_target(new_state, target):
                break

        return trajectory

    def _extract_target(self, scenario: Scenario) -> np.ndarray:
        """Extract target state as 12D numpy array.

        Args:
            scenario: Scenario with target_state

        Returns:
            12D target array
        """
        target_state = scenario.target_state

        # Extract spatial coordinates
        x = float(target_state.get("x", 0.0))
        y = float(target_state.get("y", 0.0))
        z = float(target_state.get("z", 0.0))

        # Default HIHO dimensions to 0.5
        target = np.array(
            [
                x,
                y,
                z,
                0.0,  # temporal
                0.5,  # physics
                0.5,  # biology
                0.5,  # logic
                0.5,  # quantum
                0.5,  # field
                0.5,  # control
                0.5,  # novelty
                0.0,  # precipitation
            ]
        )

        return target

    def _validate_morphospace(
        self, scenario: Scenario, target: np.ndarray
    ) -> np.ndarray:
        """Validate that stability wells are not degenerate.

        Args:
            scenario: Scenario with competing objectives
            target: Current target

        Returns:
            Validated target (or regenerated if degenerate)
        """
        if not scenario.competing_objectives or len(scenario.competing_objectives) < 2:
            return target

        # Extract positions of all wells
        positions = []
        for obj in scenario.competing_objectives:
            x = float(obj.get("x", 0.0))
            y = float(obj.get("y", 0.0))
            positions.append(np.array([x, y]))

        # Check pairwise distances
        min_distance = float("inf")
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                distance = np.linalg.norm(positions[i] - positions[j])
                min_distance = min(min_distance, distance)

        # If wells too close (degenerate), add small perturbation
        if min_distance < 0.1:
            logger.warning("Degenerate morphospace detected, adding perturbation")
            target[:2] += np.random.uniform(-0.2, 0.2, size=2)

        return target

    def _add_ambiguity_noise(
        self, target: np.ndarray, ambiguity_level: float
    ) -> np.ndarray:
        """Add noise to target based on ambiguity level.

        Args:
            target: Target state
            ambiguity_level: Ambiguity (0.0-1.0)

        Returns:
            Noisy target
        """
        noise = np.random.uniform(
            -ambiguity_level * 0.3, ambiguity_level * 0.3, size=12
        )
        return target + noise

    def _should_interrupt(self, scenario: Scenario, step: int) -> bool:
        """Check if interruption should occur at this step.

        Args:
            scenario: Scenario with interruptions
            step: Current step number

        Returns:
            True if should interrupt
        """
        for interruption in scenario.interruptions:
            interrupt_step_val = interruption.get("step", -1)
            interrupt_step = (
                int(interrupt_step_val)
                if isinstance(interrupt_step_val, (int, float))
                else -1
            )
            if interrupt_step == step:
                return True
        return False

    def _apply_interruption(
        self, scenario: Scenario, agent: EVOAgent, step: int
    ) -> None:
        """Apply interruption (context switch) to agent.

        Args:
            scenario: Scenario with interruption definition
            agent: Agent to interrupt
            step: Current step
        """
        for interruption in scenario.interruptions:
            interrupt_step_val = interruption.get("step", -1)
            interrupt_step = (
                int(interrupt_step_val)
                if isinstance(interrupt_step_val, (int, float))
                else -1
            )

            if interrupt_step == step:
                # Force state change (context reset)
                current = agent.to_numpy()
                # Apply forced state if specified
                forced_x = interruption.get("forced_state_x")
                forced_y = interruption.get("forced_state_y")
                if forced_x is not None:
                    current[0] = float(forced_x)
                if forced_y is not None:
                    current[1] = float(forced_y)

                # Add voltage spike (represents interruption)
                current += np.random.uniform(-0.1, 0.1, size=12)

                agent.update_from_numpy(current)
                logger.debug(f"Applied interruption at step {step}")
                break

    def _reached_target(self, state: np.ndarray, target: np.ndarray) -> bool:
        """Check if agent reached target.

        Args:
            state: Current state
            target: Target state

        Returns:
            True if within threshold distance
        """
        distance = np.linalg.norm(state - target)
        return bool(distance < 0.1)
