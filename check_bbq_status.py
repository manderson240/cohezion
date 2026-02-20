import asyncio

from cohezion.core.persistence.surreal_client import SurrealClient


async def check():
    db = SurrealClient()
    await db.connect()
    try:
        # Check specifically for the BBQ checkpoints
        query = 'SELECT * FROM agent_journeys WHERE journey_id ~ "sim_bbq" ORDER BY started_at DESC LIMIT 1'
        res = await db.query(query)
        print(f"BBQ LATEST: {res}")
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(check())
