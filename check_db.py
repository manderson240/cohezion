import asyncio
from cohezion.core.persistence.surreal_client import SurrealClient

async def check():
    db = SurrealClient()
    await db.connect()
    
    print("\n--- ALL agent_journeys ---")
    res_j = await db.query('SELECT * FROM agent_journeys')
    print(res_j)
    
    await db.close()

if __name__ == "__main__":
    asyncio.run(check())
