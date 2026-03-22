import asyncio
import logging

from cohezion.core.persistence.surreal_client import SurrealClient


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("DBAnalyze")


async def analyze():
    client = SurrealClient()
    await client.connect()

    logger.info("📊 FINAL AUDIT of SurrealDB Tables...")
    try:
        tables_res = await client.query("INFO FOR DB")
        tables_info = tables_res[0].get("result", {}) if isinstance(tables_res[0], dict) else tables_res[0]
        tables = tables_info.get("tables", {}).keys()

        for table in tables:
            count_res = await client.query(f"SELECT count() FROM {table} GROUP ALL")
            count = 0
            if count_res and isinstance(count_res, list):
                # Standard SurrealDB response is a list of results
                # Each result is a list of records (for this group all query)
                result_item = count_res[0]
                records = result_item.get("result", []) if isinstance(result_item, dict) else result_item
                if records and isinstance(records, list) and len(records) > 0:
                    count = records[0].get("count", 0)

            logger.info(f" - Table '{table}': {count} records")

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(analyze())
