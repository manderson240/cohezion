import asyncio

from cohezion.core.persistence.surreal_client import SurrealClient


async def check_narration():
    client = SurrealClient()
    await client.connect()
    # Check the last 5 nodes for narration in metadata
    res = await client.query("SELECT metadata.narration FROM universe_nodes LIMIT 5")
    print(f"Narrations found: {res}")
    await client.close()


if __name__ == "__main__":
    asyncio.run(check_narration())
