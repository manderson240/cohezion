import asyncio
import json
import logging
from pathlib import Path

from cohezion.core.persistence.surreal_client import SurrealClient, UniverseNode


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SimulationIngestor")


async def ingest_overnight_cache():
    """
    Ingest simulation events from cache/swarm/*.json into SurrealDB.
    Fixes the 'SurrealDB Down' issue from the overnight run.
    """
    client = SurrealClient()
    cache_dir = Path("cache/swarm")

    if not cache_dir.exists():
        logger.error("Cache directory not found.")
        return

    json_files = list(cache_dir.glob("*.json"))
    logger.info(f"Found {len(json_files)} cached thought nodes to ingest.")

    success_count = 0
    for jp in json_files:
        try:
            data = json.loads(jp.read_text())
            # Map cache schema to UniverseNode
            node = UniverseNode(
                id=jp.stem[:32],  # Use part of hash as ID
                content=data.get("response", ""),
                embedding=data.get("embedding"),
                node_type="agent_thought",
                metadata={
                    "model": data.get("model"),
                    "phi_score": data.get("phi_score"),
                    "timestamp": data.get("timestamp"),
                },
            )

            await client.store_node(node)
            success_count += 1
        except Exception as e:
            logger.warning(f"Failed to ingest {jp.name}: {e}")

    logger.info(f"Successfully ingested {success_count}/{len(json_files)} nodes into SurrealDB.")


if __name__ == "__main__":
    asyncio.run(ingest_overnight_cache())
