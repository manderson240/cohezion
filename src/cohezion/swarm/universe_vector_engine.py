import time

import numpy as np


class UniverseVectorEngine:
    """
    Parametric vectorized engine for Multiverse scenario modeling.
    Allows overriding fundamental physics constants per simulation.
    """

    PARAM_NAMES = [
        "Awareness",
        "Space_1",
        "Space_2",
        "Space_3",
        "Tempic",
        "Electric",
        "Magnetic",
        "Spin_Rotation",
        "Spin_Precession",
        "Charge_Polarity",
        "Particularization",
        "Precipitation",
    ]

    def __init__(self, num_rounds: int = 1_000_000):
        self.num_rounds = num_rounds
        self.dims = 12

    def run_scenario(
        self,
        name: str,
        momentum: float = 0.9,
        coupling: float = 1.0,
        hiho_target: float = 0.5,
        entropy: float = 0.02,
        swarm_enabled: bool = True,
        flume_enabled: bool = True,
        hiho_enabled: bool = True,
    ):
        """
        Runs a simulation with parametric overrides.
        """
        start_time = time.perf_counter()

        # 1. Base States (0 to 1)
        # We use 'entropy' as the drift factor in the random walk
        states = np.zeros((self.num_rounds, self.dims))
        states[0] = np.random.rand(self.dims)

        if flume_enabled:
            for i in range(1, self.num_rounds):
                # Momentum-based random walk: higher entropy = larger drift
                drift = (np.random.rand(self.dims) - 0.5) * entropy
                states[i] = np.clip(states[i - 1] + drift, 0, 1)
        else:
            states = np.random.rand(self.num_rounds, self.dims)

        # 2. Swarm Dynamics (Coupling)
        if swarm_enabled:
            # Coupling factor modulates how strongly Awareness affects Fields
            field_overlap = np.mean(states[:, 4:7], axis=1) * states[:, 0] * coupling
            field_overlap = np.clip(field_overlap, 0, 1)

            rotation_sign = np.sign(states[:, 7] - 0.5)
            precession_sign = np.sign(states[:, 8] - 0.5)
            charge_polarity = rotation_sign + 0.3 * precession_sign
            states[:, 9] = (charge_polarity + 1.3) / 2.6
            spin_coherence = np.abs(rotation_sign * precession_sign)
        else:
            field_overlap = np.mean(states[:, 4:7], axis=1)
            spin_coherence = 1.0

        # 3. Stability Logic (HIHO)
        if hiho_enabled:
            # Shift the stability center based on hiho_target
            # A centered 0.5 target is the 'Golden Mean'
            stability = (1.0 - np.abs(field_overlap - hiho_target) * 2) * (
                0.7 + 0.3 * spin_coherence
            )
        else:
            stability = field_overlap * (0.7 + 0.3 * spin_coherence)

        stability = np.clip(stability, 0, 1)

        # 4. Precipitation
        precipitation_mask = field_overlap > hiho_target
        precipitated_reality = states[:, 11] * stability * precipitation_mask

        # 5. Bright Spots (Top 0.1% of stability/reality)
        bright_spots_mask = (stability > 0.95) & (precipitated_reality > 0.5)
        bright_spot_indices = np.where(bright_spots_mask)[0]

        duration = time.perf_counter() - start_time

        return {
            "scenario_name": name,
            "num_rounds": self.num_rounds,
            "duration": duration,
            "bright_spot_count": int(len(bright_spot_indices)),
            "bright_spot_samples": states[bright_spot_indices[:100]].tolist()
            if len(bright_spot_indices) > 0
            else [],
            "mean_stability": float(np.mean(stability)),
            "max_reality": float(np.max(precipitated_reality))
            if len(precipitated_reality) > 0
            else 0.0,
            "params": {
                "momentum": momentum,
                "coupling": coupling,
                "hiho_target": hiho_target,
                "entropy": entropy,
            },
        }
