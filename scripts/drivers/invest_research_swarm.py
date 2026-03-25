import asyncio
import logging
from datetime import datetime

import psutil
from cohezion.mcp.email_notifier import EmailNotifier

from cohezion.core.persistence.surreal_client import (
    PhysicsState,
    SurrealClient,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("eco_research_swarm.log"), logging.StreamHandler()],
)
logger = logging.getLogger("EcoResearchSwarm")


class EcoResearchSwarm:
    """
    Background swarm that abstracts InVEST models to evaluate universal natural capital.
    Runs concurrently with the simulation driver.
    """

    def __init__(self, update_interval_seconds: int = 300):
        self.db = SurrealClient()
        self.email = EmailNotifier()
        self.update_interval = update_interval_seconds
        self.processed_ids = set()

    async def run(self):
        logger.info("🌿 Eco-Lattice Research Swarm deployed.")
        await self.db.connect()

        while True:
            # 1. Resource Check (Strict to avoid collision with Simulation Mission)
            if self._check_resource_safety():
                # 2. Analyze latest simulation data
                try:
                    await self._analyze_ecosystemic_trends()
                except Exception as e:
                    logger.error(f"Ecosystemic analysis failed: {e}")
            else:
                logger.debug("Eco-Swarm idling... Simulation engine has priority.")

            await asyncio.sleep(self.update_interval)

    def _check_resource_safety(self) -> bool:
        cpu_usage = psutil.cpu_percent(interval=None)
        # Relaxed threshold to allow parallel research during high-throughput runs
        return not cpu_usage > 90

    async def _analyze_ecosystemic_trends(self):
        """Perform InVEST-based abstraction analysis on simulation nodes."""
        # Query for nodes that haven't been 'eco-valued' yet
        query = "SELECT * FROM universe_nodes WHERE metadata.eco_valued IS NONE LIMIT 100"
        try:
            results = await self.db.query(query)
            # The client returns a list of records directly in this version
            nodes = results if results else []
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return

        if not nodes:
            return

        logger.info(f"Analyzing {len(nodes)} nodes for ecosystemic value...")

        for node in nodes:
            if not isinstance(node, dict):
                logger.warning(f"Skipping non-dict node: {type(node)}")
                continue
            try:
                # 1. Extract Physics State (handle dict or packed string)
                p_raw = node.get("physics_state")

                # If it's a string, it might be the packed base64
                if isinstance(p_raw, str):
                    p = PhysicsState.unpack(p_raw).to_dict()
                elif isinstance(p_raw, dict):
                    p = p_raw
                else:
                    # Try falling back to packed_physics field
                    packed = node.get("packed_physics")
                    if packed:
                        p = PhysicsState.unpack(packed).to_dict()
                    else:
                        logger.warning(f"Node {node['id']} has no physics data.")
                        continue

                # 2. Abstract InVEST Metrics
                # dim_5_mass, dim_10_stability, etc.
                mass = p.get("dim_5_mass", 0)
                stability = p.get("dim_10_stability", 0)
                connectivity = p.get("dim_9_connectivity", 0)

                # 3. Valuation Logic
                info_density = (mass + stability) / 2.0
                energy_flow = connectivity

                goldilocks_deviation = abs(stability - 0.5)
                habitat_quality = max(0.0, 1.0 - (goldilocks_deviation * 2))

                # ID can be a RecordID object, cast to string for splitting
                str(node["id"])

                # Update Node Metadata
                eco_metrics = {
                    "info_density": float(info_density),
                    "energy_flow": float(energy_flow),
                    "habitat_quality": float(habitat_quality),
                    "eco_evaluation_time": datetime.now().isoformat(),
                }

                # Surgical update using the direct record ID to avoid full-record schema validation issues
                update_res = await self.db.query(
                    "UPDATE $id SET metadata.eco_metrics = $eco, metadata.eco_valued = true",
                    {"eco": eco_metrics, "id": node["id"]},
                )
                logger.info(f"Update result for {node['id']}: {update_res}")
            except Exception as e:
                logger.error(f"Failed to process node {node.get('id')}: {e}")

        logger.info("Batch eco-valuation complete.")


if __name__ == "__main__":
    swarm = EcoResearchSwarm()
    asyncio.run(swarm.run())
