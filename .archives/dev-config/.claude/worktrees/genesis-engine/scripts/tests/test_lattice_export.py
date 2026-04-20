import asyncio
import json
import logging
from pathlib import Path

from cohezion.core.persistence.surreal_client import SurrealClient


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LatticeTest")


async def test_export():
    db = SurrealClient()
    logger.info("Connecting to DB...")

    try:
        # Test Query (No Order By to avoid index issues)
        query = "SELECT id, created_at, metadata.topic, metadata.grade, metadata.verified FROM universe_nodes WHERE node_type = 'research_paper' LIMIT 100"
        logger.info(f"Running Query: {query}")

        response = await db.query(query)
        logger.info(f"Response Type: {type(response)}")

        nodes = []
        if isinstance(response, list) and response and isinstance(response[0], dict):
            items = response[0].get("result", [])
            logger.info(f"Retrieved {len(items)} items.")

            for i, item in enumerate(items):
                import math

                idx = i
                phi = math.acos(-1 + (2 * idx) / 50)
                theta = math.sqrt(50 * math.pi) * phi

                x = 2.5 * math.cos(theta) * math.sin(phi)
                y = 2.5 * math.sin(theta) * math.sin(phi)
                z = 2.5 * math.cos(phi)

                nodes.append(
                    {
                        "id": item["id"],
                        "topic": item["metadata"].get("topic", "Unknown"),
                        "grade": item["metadata"].get("grade", 0.0),
                        "verified": item["metadata"].get("verified", False),
                        "position": [x, y, z],
                    }
                )

        target = Path("apps/webapp/public/data/lattice.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"nodes": nodes}))
        logger.info(f"✅ Exported to {target}")

    except Exception as e:
        logger.error(f"❌ Failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_export())
