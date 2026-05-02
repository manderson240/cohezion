"""
Bioelectric Action Vectors - Maps Levin's bioelectric signaling to COHEZION.

Compound Engineering: Uses LCSP predictor and Morphospace Mapper.
COHEZION = 0.5 HIHO drives stability.
"""

import logging
from dataclasses import dataclass

import numpy as np

from cohezion.flume.lcsp import HIHO, LCSPPredictor
from cohezion.flume.morphospace import MorphospaceMapper, StabilityWell


logger = logging.getLogger(__name__)


@dataclass
class BioelectricSignal:
    """A bioelectric signal in the morphospace."""

    voltage: float  # -1.0 to 1.0 (depolarized to hyperpolarized)
    gradient: np.ndarray  # 12D direction
    intensity: float  # Signal strength
    pattern: str  # "morphogenic", "regenerative", "homeostatic"


@dataclass
class ActionVector:
    """An action vector derived from bioelectric signals."""

    direction: np.ndarray  # 12D unit vector
    magnitude: float
    target_well: StabilityWell | None
    confidence: float


class BioelectricEngine:
    """
    Maps bioelectric signaling patterns to 12D action vectors.

    Based on Michael Levin's morphogenetic field concepts:
    - Bioelectric patterns encode target morphology
    - Cells navigate morphospace to "preferred shapes"
    - COHEZION = 0.5 HIHO is the stability attractor
    """

    def __init__(
        self,
        predictor: LCSPPredictor | None = None,
        mapper: MorphospaceMapper | None = None,
    ):
        self.predictor = predictor or LCSPPredictor()
        self.mapper = mapper or MorphospaceMapper(self.predictor)

    def encode_signal(
        self,
        current_state: np.ndarray,
        target_state: np.ndarray,
    ) -> BioelectricSignal:
        """
        Encode a bioelectric signal from current to target state.

        The voltage represents distance from HIHO stability.
        """
        # Gradient towards target
        gradient = target_state - current_state
        gradient_norm = np.linalg.norm(gradient)
        if gradient_norm > 0:
            gradient = gradient / gradient_norm

        # Voltage: deviation from HIHO
        current_coherence = np.mean(np.abs(current_state))
        voltage = (current_coherence - HIHO) * 2  # Scale to -1, 1

        # Intensity based on distance
        intensity = min(1.0, gradient_norm)

        # Pattern classification
        if intensity < 0.1:
            pattern = "homeostatic"
        elif abs(voltage) > 0.3:
            pattern = "regenerative"
        else:
            pattern = "morphogenic"

        return BioelectricSignal(
            voltage=voltage,
            gradient=gradient,
            intensity=intensity,
            pattern=pattern,
        )

    def decode_action(
        self,
        signal: BioelectricSignal,
        current_state: np.ndarray,
    ) -> ActionVector:
        """
        Decode a bioelectric signal into an action vector.
        """
        # Find target well based on signal direction
        projected_state = current_state + signal.gradient * signal.intensity
        target_well = self.mapper.find_nearest_well(projected_state)

        # LCSP prediction for refined direction
        prediction = self.predictor.predict(current_state)

        # Blend signal gradient with LCSP prediction
        direction = HIHO * signal.gradient + (1 - HIHO) * np.array(prediction.actions)
        direction_norm = np.linalg.norm(direction)
        if direction_norm > 0:
            direction = direction / direction_norm

        # Magnitude modulated by voltage (closer to HIHO = stronger)
        magnitude = signal.intensity * (1.0 - abs(signal.voltage))

        return ActionVector(
            direction=direction,
            magnitude=magnitude,
            target_well=target_well,
            confidence=prediction.confidence,
        )

    def step(
        self,
        state: np.ndarray,
        target: np.ndarray | None = None,
        step_size: float = 0.1,
    ) -> tuple[np.ndarray, ActionVector]:
        """
        Take one bioelectric-guided step in morphospace.

        Args:
            state: Current 12D state
            target: Optional target state (defaults to HIHO origin)
            step_size: How far to move

        Returns:
            (new_state, action_vector)
        """
        if target is None:
            target = np.full(12, HIHO)  # Default to HIHO stability

        signal = self.encode_signal(state, target)
        action = self.decode_action(signal, state)

        new_state = state + action.direction * action.magnitude * step_size
        new_state = np.clip(new_state, -1.0, 1.0)

        return new_state, action

    def simulate_morphogenesis(
        self,
        initial_state: np.ndarray,
        target_well: StabilityWell,
        max_steps: int = 100,
    ) -> list[tuple[np.ndarray, BioelectricSignal]]:
        """
        Simulate morphogenetic development guided by bioelectric signals.
        """
        trajectory = []
        state = initial_state.copy()

        for _ in range(max_steps):
            signal = self.encode_signal(state, target_well.center)
            trajectory.append((state.copy(), signal))

            # Check if reached target
            if np.linalg.norm(state - target_well.center) < target_well.radius:
                break

            # Take step
            state, _ = self.step(state, target_well.center)

        return trajectory


if __name__ == "__main__":
    engine = BioelectricEngine()

    # Simulate morphogenesis to HIHO origin
    initial = np.random.randn(12) * 0.3
    target = engine.mapper.known_wells[0]  # HIHO_Origin

    trajectory = engine.simulate_morphogenesis(initial, target)

    print(f"Morphogenesis to {target.name}:")
    print(f"  Steps: {len(trajectory)}")
    print(f"  Initial pattern: {trajectory[0][1].pattern}")
    print(f"  Final pattern: {trajectory[-1][1].pattern}")
    print(f"  Final voltage: {trajectory[-1][1].voltage:.3f}")
