import numpy as np
import time
from pathlib import Path

class HihoVectorEngine:
    """
    Highly optimized vectorized engine for mass HIHO simulations.
    Implements Wilbert Smith's 12-parameter reality model.
    """

    PARAM_NAMES = [
        "Awareness", "Space_1", "Space_2", "Space_3",
        "Tempic", "Electric", "Magnetic",
        "Spin_Rotation", "Spin_Precession", "Charge_Polarity",
        "Particularization", "Precipitation"
    ]

    def __init__(self, num_rounds=10_000_000):
        self.num_rounds = num_rounds
        self.dims = 12

    def calculate_hiho_score(self, coherence: float) -> float:
        """
        Calculates stability centered at exactly 0.5.
        Penalizes chaos (0.0) and overconfidence (1.0).

        This aligns with Anthropic's calibration goals: 1.0 is a
        dangerous 'hallucination zone' if not grounded.
        """
        # Linear decay from 0.5
        score = 1.0 - abs(coherence - 0.5) * 2
        return float(np.clip(score, 0, 1))

    def run_simulation(self,
                       swarm_enabled: bool = True,
                       flume_enabled: bool = True,
                       hiho_enabled: bool = True):
        """
        Runs the simulation with optional platform improvements.
        """
        start_time = time.perf_counter()

        # 1. Base States (0 to 1)
        if flume_enabled:
            # FLUME adds temporal momentum (correlated random walk)
            states = np.zeros((self.num_rounds, self.dims))
            states[0] = np.random.rand(self.dims)
            momentum = 0.9
            for i in range(1, self.num_rounds):
                # Proper random walk with clipping
                drift = (np.random.rand(self.dims) - 0.5) * 0.02
                states[i] = np.clip(states[i-1] + drift, 0, 1)
        else:
            states = np.random.rand(self.num_rounds, self.dims)

        # 2. Swarm Dynamics (Coupling)
        if swarm_enabled:
            # SWARM logic: Awareness (0) modulates Field Fabric (4:7)
            field_overlap = np.mean(states[:, 4:7], axis=1) * states[:, 0]
            # Rotation & Precession (7:9) coupling for Charge (9)
            rotation_sign = np.sign(states[:, 7] - 0.5)
            precession_sign = np.sign(states[:, 8] - 0.5)
            charge_polarity = rotation_sign + 0.3 * precession_sign
            states[:, 9] = (charge_polarity + 1.3) / 2.6
            spin_coherence = np.abs(rotation_sign * precession_sign)
        else:
            # Baseline: Independent dimensions
            field_overlap = np.mean(states[:, 4:7], axis=1)
            spin_coherence = 1.0 # No spin penalty in baseline

        # 3. Stability Logic (HIHO)
        if hiho_enabled:
            # Max stability at 0.5
            stability = (1.0 - np.abs(field_overlap - 0.5) * 2) * (0.7 + 0.3 * spin_coherence)
        else:
            # Baseline: High coherence = High stability (Dangerous overconfidence)
            stability = field_overlap * (0.7 + 0.3 * spin_coherence)

        stability = np.clip(stability, 0, 1)

        # 4. Precipitation
        if hiho_enabled:
            precipitation_mask = field_overlap > 0.5
        else:
            precipitation_mask = field_overlap > 0.8 # Higher bar for 'reality' in baseline

        precipitated_reality = states[:, 11] * stability * precipitation_mask

        # 5. Bright Spots
        bright_spots_mask = (stability > 0.9) & (precipitated_reality > 0)
        bright_spot_indices = np.where(bright_spots_mask)[0]

        duration = time.perf_counter() - start_time

        return {
            "num_rounds": self.num_rounds,
            "duration": duration,
            "bright_spot_count": len(bright_spot_indices),
            "bright_spot_states": states[bright_spot_indices[:1000]] if len(bright_spot_indices) > 0 else np.array([]),
            "mean_stability": np.mean(stability),
            "max_reality": np.max(precipitated_reality) if len(precipitated_reality) > 0 else 0
        }

if __name__ == "__main__":
    engine = HihoVectorEngine(num_rounds=10_000_000)
    results = engine.run_simulation()

    # Save results summary
    output_path = Path("/home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph/hiho_results.json")
    # Convert numpy arrays to lists for JSON
    serializable_results = {
        "num_rounds": results["num_rounds"],
        "duration": results["duration"],
        "bright_spot_count": results["bright_spot_count"],
        "mean_stability": float(results["mean_stability"]),
        "max_reality": float(results["max_reality"]),
        "bright_spot_samples": results["bright_spot_states"][:10].tolist()
    }

    import json
    output_path.write_text(json.dumps(serializable_results, indent=2))
    print(f"💾 Results saved to {output_path}")
