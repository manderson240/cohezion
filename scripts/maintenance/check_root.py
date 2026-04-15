import asyncio
import os
import sys

# Add src to PYTHONPATH
sys.path.append(os.path.join(os.getcwd(), "src"))

from cohezion.core.persistence.surreal_client import SurrealClient


async def main():
    db = SurrealClient(url="ws://localhost:8001/rpc")
    await db.connect()
    # Check namespaces at root level
    root_info = await db.query("INFO FOR ROOT;")
    print(f"ROOT INFO: {root_info}")

    namespaces = root_info.get("namespaces", {}) if isinstance(root_info, dict) else {}
    for ns in namespaces.keys():
        print(f"\n--- Namespace: {ns} ---")
        await db.query(f"USE NS {ns};")
        ns_info = await db.query("INFO FOR NS;")
        databases = ns_info.get("databases", {}) if isinstance(ns_info, dict) else {}
        for db_name in databases.keys():
            print(f"  --- Database: {db_name} ---")
            await db.query(f"USE DB {db_name};")
            db_info = await db.query("INFO FOR DB;")
            tables = db_info.get("tables", {}) if isinstance(db_info, dict) else {}
            print(f"    Tables: {list(tables.keys())}")

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
