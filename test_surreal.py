from cohezion.db.surreal_client import SurrealClient
import asyncio

async def test():
    client = SurrealClient()
    print(f"Has create: {hasattr(client, 'create')}")
    print(dir(client))

if __name__ == "__main__":
    asyncio.run(test())
