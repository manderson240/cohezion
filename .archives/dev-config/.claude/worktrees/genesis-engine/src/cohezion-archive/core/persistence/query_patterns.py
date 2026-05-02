import asyncio
import os

from surrealdb import AsyncSurreal


async def query_patterns():
    async with AsyncSurreal("ws://localhost:8000/rpc") as db:
        await db.signin(
            {
                "username": os.environ.get("SURREAL_USER", "root"),
                "password": os.environ.get("SURREAL_PASSWORD", "root"),
            }
        )
        await db.use("cohezion", "universe")

        # List all tables
        results = await db.query("INFO FOR DB")
        print("DATABASE INFO:")
        print(results)

        # Check if table exists and count
        results = await db.query("SELECT count() FROM universe_nodes GROUP ALL")
        print("\nNODE COUNT:")
        print(results)


if __name__ == "__main__":
    asyncio.run(query_patterns())
