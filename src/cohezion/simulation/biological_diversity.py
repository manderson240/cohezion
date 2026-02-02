import random
import logging
from dataclasses import dataclass
from typing import Dict, List

logger = logging.getLogger("BiologicalDiversity")

@dataclass
class BiologicalSubstrate:
    name: str
    primary_element: str
    stability_threshold: float
    coherence_multiplier: float
    entropy_rate: float

class BiologicalDiversityEngine:
    """
    Simulates self-organization potentials across different biological substrates.
    Integrated into the 12D manifold simulation.
    """
    
    SUBSTRATES = {
        "carbon": BiologicalSubstrate("Carbon-Based", "C", 0.5, 1.0, 0.1),
        "silicon": BiologicalSubstrate("Silicon-Based", "Si", 0.7, 0.9, 0.05),
        "arsenic": BiologicalSubstrate("Arsenic-Extremophile", "As", 0.3, 1.1, 0.15),
        "plasma": BiologicalSubstrate("Conscious Plasma", "Ion", 0.85, 1.5, 0.4),
        "quark_gluon": BiologicalSubstrate("Quark-Gluon Soup", "QGP", 0.9, 2.0, 0.5),
        "quantum_foam": BiologicalSubstrate("Quantum Foam Form", "Planck", 0.95, 3.0, 0.8),
        "crystalline": BiologicalSubstrate("Piezo-Crystalline", "SiO2", 0.65, 1.2, 0.02)
    }

    def __init__(self):
        self.active_substrate = "carbon"
        self.hypothesis_log = []
        
    def select_substrate(self, hiho_coherence: float):
        """Select substrate based on simulation resonance."""
        if hiho_coherence > 0.9:
            self.active_substrate = random.choice(["quantum_foam", "quark_gluon"])
        elif hiho_coherence > 0.75:
            self.active_substrate = "plasma"
        elif hiho_coherence > 0.6:
            self.active_substrate = random.choice(["silicon", "crystalline"])
        elif hiho_coherence > 0.4:
            self.active_substrate = "carbon"
        else:
            self.active_substrate = "arsenic"
            
        logger.info(f"🧬 Substrate Resonator shifted to: {self.active_substrate}")

    def hypothesize_novel_form(self, novelty_index: float) -> str:
        """Hypothesize a new biological form based on novel physics."""
        if novelty_index > 0.8 and random.random() < 0.3:
            prefixes = ["Hyper", "Quantum", "Fractal", "Neutron", "Dark", "Tachyon", "Void"]
            bases = ["Mycelium", "Lattice", "Vortex", "Swarm", "Condensate", "Coral"]
            new_form = f"{random.choice(prefixes)}-{random.choice(bases)}"
            if new_form not in self.hypothesis_log:
                self.hypothesis_log.append(new_form)
                logger.info(f"🧪 HYPOTHESIS: Detected potential for {new_form} life-forms.")
                return new_form
        return None

    def simulate_self_organization(self, state_12d: List[float]) -> Dict:
        """Calculate organization metrics for the current substrate."""
        substrate = self.SUBSTRATES[self.active_substrate]
        
        # Stability is influenced by 12D entropy and substrate threshold
        avg_vibe = sum(state_12d) / 12
        organization_potential = avg_vibe * substrate.coherence_multiplier
        
        # Check for novel hypothesis
        novel_form = self.hypothesize_novel_form(avg_vibe)
        
        survival_probability = 1.0 if organization_potential > substrate.stability_threshold else organization_potential / substrate.stability_threshold
        
        return {
            "substrate": substrate.name,
            "potential": organization_potential,
            "survival": survival_probability,
            "entropy_delta": substrate.entropy_rate * (1 - survival_probability),
            "hypothesis": novel_form
        }

def get_diversity_engine() -> BiologicalDiversityEngine:
    return BiologicalDiversityEngine()
