import asyncio
import os
import sys

# Add src to PYTHONPATH
sys.path.append(os.path.join(os.getcwd(), "src"))

from cohezion.core.persistence.surreal_client import SurrealClient

async def main():
    db = SurrealClient(url="ws://localhost:8001/rpc")
    await db.connect()
    # Check namespaces
    ns_info = await db.query("INFO FOR NS;")
    print(f"NS INFO: {ns_info}")
    
    # Try common namespaces
    for ns in ["cohezion", "universe", "test", "default"]:
        await db.query(f"USE NS {ns};")
        res = await db.query("INFO FOR NS;")
        print(f"INFO FOR NS {ns}: {res}")
        
    await db.close()

if __name__ == "__main__":
    asyncio.run(main())
