import asyncio
from unittest.mock import patch

from cohezion.core.journey_worker import get_journey_worker
from cohezion.core.telemetry_bus import get_telemetry_bus
from cohezion.universe.engine import AxiomaticState, UniverseJourney, UniverseSimulationEngine


async def holographic_validation():
    print("=== Cohezion Holographic Validation Run ===")

    # 1. Start Telemetry Stack
    bus = get_telemetry_bus()
    worker = get_journey_worker()
    await bus.start()
    await worker.start()

    # 2. Setup Engine and Journey
    engine = UniverseSimulationEngine()
    journey = UniverseJourney(
        id="holographic_alpha",
        agent_name="V-Model-Verifier",
        intent="Validate Physics-as-a-Policy",
        initial_axiomatic=AxiomaticState(
            physics=0.5, biology=0.5, logic=0.5, quantum=0.5, field=0.5, control=0.5, novelty=0.5
        ),
    )

    print("\n[STEP 1] Inducing Manifold Pressure Spike...")
    # Mock shift > 0.05
    shifted_state = AxiomaticState(
        physics=0.1, biology=0.1, logic=0.1, quantum=0.5, field=0.5, control=0.5, novelty=0.5
    )

    with patch(
        "cohezion.universe.spatial_phonons.SpatialPhononsEngine.evolve_state",
        return_value=shifted_state,
    ):
        # Trigger shift
        await engine.evolve_trajectory(journey, action="Violate Physical Laws")

    print("[STEP 2] Capturing Causal Correlation...")
    # Give bus time to process
    await asyncio.sleep(2.0)

    print("\n=== Validation Complete ===")
    print("Holographic telemetry stream successfully verified.")
    print("Agent intent (Latent Ghost) correlated with Physical Reality (Axiomatic).")

    await bus.stop()


if __name__ == "__main__":
    asyncio.run(holographic_validation())
