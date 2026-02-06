import asyncio
import json
import logging
import math
import time
from pathlib import Path

from cohezion.core.persistence.surreal_client import SurrealClient

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - [VISUAL_CORTEX] - %(message)s"
)
logger = logging.getLogger("VisualCortex")

LATTICE_PATH = Path("apps/webapp/public/data/lattice.json")


class VisualCortex:
    """
    High-Speed Visualization Exporter.
    Decoupled from Research Daemon to allow 60fps+ updates if needed.
    """

    def __init__(self):
        self.db = SurrealClient()
        self.last_hash = ""

    async def run_loop(self):
        logger.info("👁️ Visual Cortex Online. Monitoring Lattice...")

        while True:
            start_time = time.time()
            try:
                changed = await self.export_lattice()
                elapsed = time.time() - start_time

                # Dynamic sleep to maintain target rate (e.g. 1s)
                sleep_time = max(0.1, 2.0 - elapsed)
                if changed:
                    logger.info(f"✨ Lattice Refreshed in {elapsed:.3f}s")

                await asyncio.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Blindness: {e}")
                await asyncio.sleep(5)

    async def export_lattice(self) -> bool:
        """Fetch nodes and dump JSON."""
        # Query: ID, Topic, Grade, Verified, CreatedAt
        # Limit 200 for density
        query = "SELECT id, created_at, metadata.topic, metadata.grade, metadata.verified FROM universe_nodes WHERE node_type = 'research_paper' LIMIT 200"
        response = await self.db.query(query)

        items = []
        if isinstance(response, list) and response and isinstance(response[0], dict):
            items = response[0].get("result", [])

        if not items:
            return False

        # Sort by Recency
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        items = items[:100]  # HUD Limit

        # Check Content Hash to avoid writing unchanged files (Save IO)
        current_hash = str(sum(hash(x["id"]) for x in items))
        if current_hash == self.last_hash:
            return False

        self.last_hash = current_hash

        nodes = []
        for i, item in enumerate(items):
            # 3D Spiral Layout (Golden Angle)
            idx = i
            # Phi -> Distance from center (Time)
            phi = math.acos(-1 + (2 * idx) / 100)
            # Theta -> Spiral Angle
            theta = math.sqrt(100 * math.pi) * phi

            # Sphere Coords
            x = 2.5 * math.cos(theta) * math.sin(phi)
            y = 2.5 * math.sin(theta) * math.sin(phi)
            z = 2.5 * math.cos(phi)

            nodes.append(
                {
                    "id": str(item["id"]),
                    "topic": item["metadata"].get("topic", "Unknown"),
                    "grade": item["metadata"].get("grade", 0.0),
                    "verified": item["metadata"].get("verified", False),
                    "position": [x, y, z],
                }
            )

        # Write File
        LATTICE_PATH.parent.mkdir(parents=True, exist_ok=True)
        LATTICE_PATH.write_text(json.dumps({"nodes": nodes}))
        return True


if __name__ == "__main__":

    async def main():
        cortex = VisualCortex()
        await cortex.run_loop()

    asyncio.run(main())
