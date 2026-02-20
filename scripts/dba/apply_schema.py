import asyncio
import logging
import os
import sys


# Setup paths
sys.path.append(os.path.abspath("src"))

from cohezion.core.persistence.admin import DBAdmin


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SchemaApplier")


async def apply_schema(schema_file: str):
    logger.info(f"Applying schema from: {schema_file}")

    if not os.path.exists(schema_file):
        logger.error(f"Schema file not found: {schema_file}")
        return

    with open(schema_file) as f:
        surql = f.read()

    dba = DBAdmin()
    dba = DBAdmin()
    try:
        await dba.connect()
    except Exception as e:
        logger.error(f"Failed to connect to SurrealDB: {e}")
        return

    try:
        # Split by semicolon to execute mostly separate statements if needed,
        # but SurrealDB client usually handles raw strings well.
        # We'll try sending the whole block first.
        await dba.client.query(surql)
        logger.info("✅ Schema applied successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to apply schema: {e}")
    finally:
        await dba.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python apply_schema.py <path_to_surql_file>")
        sys.exit(1)

    asyncio.run(apply_schema(sys.argv[1]))
