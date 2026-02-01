"""
Exogenic Evolution Simulator
============================
Simulates the transition from pure digital logic to "Wetware" logic.
Models the Swarm as a biological tissue with growth hormones (differentiation).
"""

import logging
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Exogenic")


class BioSiliconBridge:
    def __init__(self):
        self.coherence_threshold = 0.85
        self.tissue_health = 1.0

    def simulate_growth(self, agent_count: int, global_entropy: float) -> dict:
        """
        Simulates "Tissue Growth" based on entropy levels.
        Low entropy = High growth / Specialization.
        """
        coherence = 1.0 - global_entropy

        result = {
            "mode": "CYBERNETIC",
            "differentiation_rate": 0.0,
            "tissue_health": self.tissue_health,
        }

        if coherence > self.coherence_threshold:
            logger.info(
                "🌿 Exogenic: Warm Coherence detected. Entering BIO-TISSUE mode."
            )
            result["mode"] = "BIOLOGICAL_TISSUE"
            result["differentiation_rate"] = (
                coherence - self.coherence_threshold
            ) * 2.0

            # Differentiation: Agents "mutate" into specialists
            new_specialists = int(agent_count * result["differentiation_rate"])
            result["specialized_count"] = new_specialists

        else:
            logger.warning(
                "⚙️  Exogenic: Cold Logic dominant. Maintaining SILICON-ONLY mode."
            )

        return result

    def apply_thermal_noise(self, signal: float) -> float:
        """
        Simulates 'Warm' biological noise (Stochastic Resonance).
        """
        noise = random.uniform(-0.01, 0.01)
        return signal + noise
