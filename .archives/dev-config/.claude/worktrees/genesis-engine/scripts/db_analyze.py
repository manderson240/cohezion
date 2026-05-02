import asyncio
import logging

from cohezion.core.persistence.surreal_client import SurrealClient


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("DBAnalyze")


async def analyze():
    client = SurrealClient()
    await client.connect()

    logger.info("📊 Analyzing SurrealDB Tables...")
    try:
        # Get table info
        tables_res = await client.query("INFO FOR DB")
        # Handle both list and dict responses
        if isinstance(tables_res, list) and len(tables_res) > 0:
            tables_info = tables_res[0].get("result", {}) if isinstance(tables_res[0], dict) else tables_res[0]
        else:
            tables_info = tables_res

        tables = tables_info.get("tables", {}).keys()

        for table in tables:
            count_res = await client.query(f"SELECT count() FROM {table} GROUP ALL")
            count = 0
            if count_res:
                # If SurrealDB returns a list of results (standard)
                data = count_res[0] if isinstance(count_res, list) else count_res
                # If result is inside a 'result' key
                inner_data = data.get("result") if isinstance(data, dict) else data
                # If data is a list of counts
                if isinstance(inner_data, list) and len(inner_data) > 0:
                    item = inner_data[0]
                    count = item.get("count", 0) if isinstance(item, dict) else 0
                elif isinstance(inner_data, dict):
                    count = inner_data.get("count", 0)
            logger.info(f" - Table '{table}': {count} records")

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(analyze())
