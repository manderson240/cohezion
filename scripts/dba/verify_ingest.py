import asyncio
import logging
import sys
from pathlib import Path


# Add src to sys
sys.path.append(str(Path.cwd() / "src"))
from cohezion.core.persistence.admin import DBAdmin


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("Verifier")
fh = logging.FileHandler("verify_output.txt")
logger.addHandler(fh)


async def verify():
    dba = DBAdmin()
    await dba.connect()

    logger.info("🔍 Verifying SurrealDB Ingestion...")

    # 1. Count Records
    try:
        # DBAdmin wraps client.query
        logger.info("👉 Querying Table Info...")
        res_info = await dba.client.query("INFO FOR TABLE universe_nodes")
        logger.info(f"📊 Table Info: {res_info}")

        logger.info("👉 Querying Count...")
        # Try simpler count
        res = await dba.client.query("SELECT count() FROM universe_nodes GROUP ALL")
        logger.info(f"🔢 Count Result: {res}")

    except Exception as e:
        logger.error(f"❌ Count query failed: {e}")

    # 2. Spot Check
    try:
        logger.info("👉 Spot Check...")
        res = await dba.client.query("SELECT * FROM universe_nodes LIMIT 1")
        logger.info(f"👀 Sample Record: {res}")

    except Exception as e:
        logger.error(f"❌ Spot check failed: {e}")

    # 3. Write Test
    try:
        logger.info("👉 Write Test...")
        test_rec = [{"type": "test_probe", "content": "Checking persistence"}]
        res_write = await dba.client.query("INSERT INTO universe_nodes $rec", {"rec": test_rec})
        logger.info(f"✍️ Write Result: {res_write}")

        # Check count again
        res_count = await dba.client.query("SELECT count() FROM universe_nodes GROUP ALL")
        logger.info(f"🔢 Count After Write: {res_count}")

    except Exception as e:
        logger.error(f"❌ Write test failed: {e}")

    await dba.close()


if __name__ == "__main__":
    asyncio.run(verify())
