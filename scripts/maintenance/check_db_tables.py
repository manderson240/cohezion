import asyncio
import os
import sys


# Add src to PYTHONPATH
sys.path.append(os.path.join(os.getcwd(), "src"))

from cohezion.core.persistence.surreal_client import SurrealClient


async def main():
    db = SurrealClient(url="ws://localhost:8001/rpc", namespace="cohezion")
    await db.connect()

    for db_name in ["cohezion", "experiments", "genesis", "universe", "vault"]:
        print(f"\n--- Database: {db_name} ---")
        await db.query(f"USE DB {db_name};")
        info = await db.query("INFO FOR DB;")
        tables = info.get("tables", {}) if isinstance(info, dict) else {}
        print(f"Tables: {list(tables.keys())}")

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
