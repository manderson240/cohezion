import asyncio
import logging
from datetime import datetime, timedelta

from cohezion.core.persistence.surreal_client import SurrealClient


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DBPruning")


async def prune_db(days=7):
    client = SurrealClient()
    await client.connect()

    threshold = (datetime.now() - timedelta(days=days)).isoformat()
    logger.info(f"🧹 Pruning SurrealDB data older than {days} days (threshold: {threshold})")

    # Tables with 'created_at' or similar timestamps
    prunable_tables = [
        "velocity_events",
        "mission_pulse",
        "agent_journeys",
    ]

    try:
        for table in prunable_tables:
            logger.info(f" - Pruning table '{table}'...")
            # SurrealDB DELETE syntax
            query = f"DELETE FROM {table} WHERE created_at < '{threshold}'"
            await client.query(query)

        # Specific cleanup for universe_nodes (agent thoughts/logs)
        logger.info(" - Pruning universe_nodes (specialized node_types)...")
        query = f"DELETE FROM universe_nodes WHERE node_type IN ['agent_thought', 'log'] AND created_at < '{threshold}'"
        await client.query(query)

    except Exception as e:
        logger.error(f"Pruning failed: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    import sys

    days = 7
    if len(sys.argv) > 1:
        days = int(sys.argv[1])
    asyncio.run(prune_db(days))
