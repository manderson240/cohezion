import asyncio

from cohezion.core.persistence.surreal_client import SurrealClient


async def check():
    client = SurrealClient()
    await client.connect()

    if hasattr(client._client, "query"):
        results = await client._client.query("SELECT * FROM universe_nodes")
        for r in results:
            if isinstance(r, dict) and r.get("node_type") == "lab_discovery":
                print(f"ID: {r.get('id')}, Success: {r.get('metadata', {}).get('verified')}")
                print(f"  Compressed: {r.get('compressed')}")
                print(f"  Packed Physics: {r.get('packed_physics')[:20]}...")
                print(f"  Narration: {r.get('metadata', {}).get('narration')}")


if __name__ == "__main__":
    asyncio.run(check())
