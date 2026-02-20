import asyncio

from cohezion.core.persistence.surreal_client import SurrealClient


async def debug():
    c = SurrealClient()
    await c.connect()
    query = "SELECT * FROM universe_nodes LIMIT 2"
    results = await c.query(query)
    print("Full Results Type:", type(results))
    print("Full Results Len:", len(results))
    if results:
        print("First Result Type:", type(results[0]))
        print("First Result Content Preview:", str(results[0])[:500])
        if isinstance(results[0], list) and results[0]:
            print("First Node Type:", type(results[0][0]))
    await c.close()


if __name__ == "__main__":
    asyncio.run(debug())
