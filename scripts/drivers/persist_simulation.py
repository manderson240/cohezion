import asyncio
import logging

# Fix path to include src if running from root
import sys
from datetime import datetime


sys.path.insert(0, "src")

from cohezion.core.persistence.surreal_client import (
    PhysicsState,
    SurrealClient,
    UniverseNode,
)
from cohezion.simulation.simulation_logger import SimulationLogger


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PersistSim")


async def persist_run():
    client = SurrealClient()
    connected = await client.connect()

    if not connected:
        logger.error("Could not connect to SurrealDB. Aborting persistence.")
        return

    logger.info("Connected to SurrealDB. Preparing node...")

    # Load recent simulation data
    sim_logger = SimulationLogger(storage_dir="data/simulations/fractal_nexus")
    try:
        dataset = sim_logger.load_universe_data(domain="fractal_nexus")
        df = dataset.to_pandas()

        if df.empty:
            logger.warning("No data to persist.")
            return

        # Calculate metrics
        avg_coherence = float(df["phi_score"].mean())
        avg_energy = float(df["energy_level"].mean())
        total_ticks = len(df["cycle_id"].unique())

        # Create Physics State for the Simulation Run
        # Mapping:
        # - Coherence -> dim_12_coherence
        # - Stability -> dim_10_stability (derived from closeness to 0.5)
        # - Complexity -> dim_7_complexity (agent count / size)

        stability = 1.0 - (abs(avg_coherence - 0.5) * 2)

        state = PhysicsState(
            x=0.0,
            y=0.0,
            z=0.0,
            time=float(total_ticks),
            mass=avg_energy,
            complexity=0.8,  # High complexity system
            stability=stability,
            coherence=avg_coherence,
            novelty=0.9,  # New biological features
        )

        node = UniverseNode(
            id=f"sim_run_fractal_nexus_{int(datetime.now().timestamp())}",
            content=f"Fractal Universe Run (Cycle 3). Evolution: Biological (Mitosis/Apoptosis). Ticks: {total_ticks}. Coherence: {avg_coherence:.4f}.",
            node_type="simulation_run",
            physics_state=state,
            metadata={
                "domain": "fractal_nexus",
                "cycles": total_ticks,
                "features": ["mitosis", "apoptosis", "dashboard_v2"],
            },
        )

        node_id = await client.store_node(node)
        logger.info(f"✅ Simulation run persisted to SurrealDB: {node_id}")

    except Exception as e:
        logger.error(f"Persistence failed: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(persist_run())
