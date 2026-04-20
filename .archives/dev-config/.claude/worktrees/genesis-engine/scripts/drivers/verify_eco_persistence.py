import asyncio

from cohezion.core.persistence.surreal_client import SurrealClient


async def main():
    c = SurrealClient()
    await c.connect()
    print("Checking metadata structure for records...")
    # The client returns a list of records directly
    records = await c.query("SELECT id, metadata FROM universe_nodes LIMIT 5")

    if records:
        for node in records:
            # Handle potential dict vs other types
            if isinstance(node, dict):
                meta = node.get("metadata", {})
                print(f"Node: {node.get('id')} | Eco Valued: {meta.get('eco_valued')}")
            else:
                print(f"Unexpected record type: {type(node)}")

    print("\nChecking for eco_valued=true...")
    eco_records = await c.query(
        "SELECT id, metadata FROM universe_nodes WHERE metadata.eco_valued = true LIMIT 5"
    )
    if eco_records:
        print(f"VERIFIED: Found {len(eco_records)} eco-valued nodes.")
        for node in eco_records:
            metrics = node["metadata"].get("eco_metrics", {})
            print(f" - {node['id']}: Habitat Quality={metrics.get('habitat_quality', 0):.4f}")
    else:
        print("Wait... No eco-valued nodes found via query yet.")

    await c.close()


if __name__ == "__main__":
    asyncio.run(main())
