import asyncio

from cohezion.core.persistence.surreal_client import SurrealClient


async def final_check():
    c = SurrealClient()
    await c.connect()

    # 1. Total nodes count
    total = await c.query("SELECT count() FROM universe_nodes GROUP ALL")
    print(f"Total Nodes: {total}")

    # 2. Check for ANY eco metrics
    print("\nChecking for any nodes with eco_metrics...")
    any_eco = await c.query(
        "SELECT id, metadata.eco_metrics FROM universe_nodes WHERE metadata.eco_metrics != NONE LIMIT 5"
    )
    print(f"Results: {any_eco}")

    # 3. Check specific valuation count
    count_eco = await c.query("SELECT count() FROM universe_nodes WHERE metadata.eco_valued = true GROUP ALL")
    print(f"Total Eco-Valued Nodes: {count_eco}")

    await c.close()


if __name__ == "__main__":
    asyncio.run(final_check())
