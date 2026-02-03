import asyncio

import numpy as np

from cohezion.swarm.advanced_physics import PHYSICS_CATALOG
from cohezion.swarm.universal_simulations import UniverseSimulator


class DirectedSimulator(UniverseSimulator):
    """
    A simulator that implements the 'Law of Swarm Recurrence'.
    Instead of random sampling, it uses recursive feedback to align the state.
    """

    async def run_epoch_directed(self, current_state: dict = None) -> dict:
        if current_state is None:
            state = self.universe.sample_state()
        else:
            # Recursive Alignment: Small drift towards 0.5 (stability center)
            state = {
                dim: np.clip(
                    val + (0.5 - val) * 0.1 + np.random.normal(0, 0.02), low, high
                )
                for (dim, val), (low, high) in zip(
                    current_state.items(),
                    self.universe.dimensions.values(),
                    strict=False,
                )
            }

        coherence = self._evaluate_coherence(state)
        paradox_tension = self._evaluate_paradoxes(state)

        emergence_score = coherence * (1 - paradox_tension * 0.5)
        emergent = emergence_score >= self.universe.emergence_threshold

        if emergent:
            pattern = self._generate_emergent_pattern(state)
            self.emergent_patterns.append(pattern)

        result = {
            "state": state,
            "coherence": coherence,
            "emergence_score": emergence_score,
            "emergent": emergent,
        }
        self.history.append(result)
        return result

    async def run_healed_simulation(self, epochs: int = 500):
        print(f"🔬 Starting Directed Simulation for: {self.universe.name}")
        state = None
        for i in range(epochs):
            res = await self.run_epoch_directed(state)
            state = res["state"]
            if i % 100 == 0:
                print(
                    f"  Step {i:3} | Coherence: {res['coherence']:.3f} | Emergence: {res['emergence_score']:.3f} | {'✨ EMERGENT' if res['emergent'] else ''}"
                )

        return {
            "name": self.universe.name,
            "patterns": len(self.emergent_patterns),
            "final_coherence": state["coherence"]
            if "coherence" in state
            else res["coherence"],
        }


async def heal_synthesis():
    spec = PHYSICS_CATALOG["evo_lenr_synthesis"]
    sim = DirectedSimulator(spec)
    result = await sim.run_healed_simulation(epochs=500)

    print("\n" + "=" * 40)
    print("HEALED SIMULATION RESULTS")
    print("=" * 40)
    print(f"Domain: {result['name']}")
    print(f"Emergent Patterns: {result['patterns']}")
    print(f"Final Coherence: {result['final_coherence']:.3f}")

    if result["patterns"] > 0:
        print(
            "\n✅ SUCCESS: Recursive Synthesis unlocked emergence in the EVO-LENR domain!"
        )
    else:
        print("\n❌ FAILURE: Emergence threshold not met.")


if __name__ == "__main__":
    asyncio.run(heal_synthesis())
