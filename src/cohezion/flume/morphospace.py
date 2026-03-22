"""
Morphospace Mapper - Navigate stability wells in the 12D manifold.

Uses LCSP predictor to find "Preferred Shapes" (stability wells).
COHEZION = 0.5 HIHO drives all stability calculations.

Compound Engineering: Built on top of LCSP predictor.
"""

import logging
from dataclasses import dataclass

import numpy as np

from cohezion.flume.lcsp import HIHO, LCSPPredictor


logger = logging.getLogger(__name__)


@dataclass
class StabilityWell:
    """A stable region in the morphospace."""

    center: np.ndarray  # 12D center point
    radius: float  # Stability radius
    depth: float  # How stable (higher = more stable)
    name: str = ""


@dataclass
class MorphoPath:
    """A path through the morphospace."""

    states: list[np.ndarray]
    stability_scores: list[float]
    total_length: float
    avg_stability: float


class MorphospaceMapper:
    """
    Maps and navigates the 12D morphospace.

    Uses LCSP predictions to find stability wells (preferred shapes)
    and navigate between them following HIHO stability gradients.
    """

    def __init__(self, predictor: LCSPPredictor | None = None):
        self.predictor = predictor or LCSPPredictor()
        self.known_wells: list[StabilityWell] = []
        self._initialize_wells()

    def _initialize_wells(self):
        """Initialize known stability wells."""
        # The origin well (pure HIHO)
        self.known_wells.append(StabilityWell(center=np.full(12, HIHO), radius=0.2, depth=1.0, name="HIHO_Origin"))

        # Awareness well (from Phase 0)
        awareness_state = np.zeros(12)
        awareness_state[0] = 1.0
        self.known_wells.append(StabilityWell(center=awareness_state, radius=0.15, depth=0.9, name="Pure_Awareness"))

    def compute_stability(self, state: np.ndarray) -> float:
        """
        Compute stability score for a 12D state.

        Uses distance from HIHO threshold (0.5).
        """
        mean_coherence = np.mean(np.abs(state))
        return 1.0 - abs(mean_coherence - HIHO)

    def find_nearest_well(self, state: np.ndarray) -> StabilityWell | None:
        """Find the nearest stability well to the given state."""
        if not self.known_wells:
            return None

        best_well = None
        best_distance = float("inf")

        for well in self.known_wells:
            distance = np.linalg.norm(state - well.center)
            if distance < best_distance:
                best_distance = distance
                best_well = well

        return best_well

    def navigate_to_well(
        self,
        start: np.ndarray,
        target_well: StabilityWell,
        max_steps: int = 50,
    ) -> MorphoPath:
        """
        Navigate from start state to target stability well.

        Uses LCSP predictions guided by HIHO stability gradient.
        """
        states = [start.copy()]
        stability_scores = [self.compute_stability(start)]

        current = start.copy()

        for _ in range(max_steps):
            # Check if we reached the well
            distance = np.linalg.norm(current - target_well.center)
            if distance < target_well.radius:
                break

            # Get LCSP prediction
            prediction = self.predictor.predict(current)

            # Blend prediction with gradient towards well center
            gradient = target_well.center - current
            gradient = gradient / (np.linalg.norm(gradient) + 1e-8)

            # HIHO-weighted blend
            next_state = HIHO * prediction.next_state + (1 - HIHO) * (current + 0.1 * gradient)

            # Normalize to reasonable range
            next_state = np.clip(next_state, -1.0, 1.0)

            states.append(next_state.copy())
            stability_scores.append(self.compute_stability(next_state))
            current = next_state

        # Compute path metrics
        total_length = sum(np.linalg.norm(states[i + 1] - states[i]) for i in range(len(states) - 1))
        avg_stability = np.mean(stability_scores)

        return MorphoPath(
            states=states,
            stability_scores=stability_scores,
            total_length=total_length,
            avg_stability=avg_stability,
        )

    def discover_wells(
        self,
        num_samples: int = 100,
        stability_threshold: float = 0.8,
    ) -> list[StabilityWell]:
        """
        Discover new stability wells by sampling the morphospace.
        """
        discovered = []

        for _ in range(num_samples):
            # Random starting point
            state = np.random.randn(12) * 0.5

            # Relax towards stability
            for _ in range(20):
                prediction = self.predictor.predict(state)
                state = prediction.next_state

            stability = self.compute_stability(state)

            if stability >= stability_threshold:
                # Check if this is a new well
                is_new = True
                for well in self.known_wells + discovered:
                    if np.linalg.norm(state - well.center) < 0.3:
                        is_new = False
                        break

                if is_new:
                    discovered.append(
                        StabilityWell(
                            center=state.copy(),
                            radius=0.2,
                            depth=stability,
                            name=f"Discovered_{len(discovered)}",
                        )
                    )

        logger.info(f"Discovered {len(discovered)} new stability wells")
        return discovered


if __name__ == "__main__":
    mapper = MorphospaceMapper()

    # Test navigation to HIHO origin
    start = np.random.randn(12) * 0.3
    target = mapper.known_wells[0]  # HIHO_Origin

    path = mapper.navigate_to_well(start, target)
    print(f"Navigation to {target.name}:")
    print(f"  Steps: {len(path.states)}")
    print(f"  Path length: {path.total_length:.3f}")
    print(f"  Avg stability: {path.avg_stability:.3f}")
    print(f"  Final stability: {path.stability_scores[-1]:.3f}")
