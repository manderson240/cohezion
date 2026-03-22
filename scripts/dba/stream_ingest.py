import asyncio
import logging

import ijson  # streaming json parser

from cohezion.core.persistence.admin import DBAdmin


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("BigIngest")

SOURCE_FILE = "/home/mike-anderson/dev/cohezion/data/sim_results_25m.json"


async def ingest_big_file():
    dba = DBAdmin()
    await dba.connect()

    logger.info(f"🚀 Streaming Ingestion of {SOURCE_FILE}")

    count = 0
    batch = []

    # Use ijson to stream the file without loading 5.5GB into RAM
    with open(SOURCE_FILE, "rb") as f:
        # File is a dict with "journey": [...]
        objects = ijson.items(f, "journey.item")

        for record in objects:
            batch.append(record)
            if len(batch) >= 2000:
                await dba.batch_ingest("universe_nodes", batch, batch_size=2000)
                count += len(batch)
                batch = []
                logger.info(f"Processed {count} records...")

        if batch:
            await dba.batch_ingest("universe_nodes", batch)
            count += len(batch)

    logger.info(f"🎉 FINAL TOTAL: {count} records ingested.")
    await dba.close()


if __name__ == "__main__":
    asyncio.run(ingest_big_file())
