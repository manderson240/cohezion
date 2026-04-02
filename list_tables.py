import asyncio
import os
import sys

# Add src to PYTHONPATH
sys.path.append(os.path.join(os.getcwd(), "src"))

from cohezion.core.persistence.surreal_client import SurrealClient

async def main():
    db = SurrealClient(url="ws://localhost:8001/rpc")
    await db.connect()
    # List all tables in the database
    res = await db.query("INFO FOR DB;")
    print(f"DB INFO: {res}")
    await db.close()

if __name__ == "__main__":
    asyncio.run(main())
