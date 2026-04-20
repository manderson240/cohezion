import asyncio
import json
import logging

from cohezion.core.persistence.surreal_client import SurrealClient


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("DBInspect")


async def inspect():
    client = SurrealClient()
    await client.connect()

    logger.info("🕵️ Inspecting remaining data...")

    tables = ["velocity_events", "mission_pulse", "agent_journeys"]
    for table in tables:
        logger.info(f" - Table '{table}':")
        res = await client.query(f"SELECT created_at, id FROM {table} LIMIT 5")
        print(f"  {json.dumps(res, indent=2)}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(inspect())
