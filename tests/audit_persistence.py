import asyncio

from cohezion.core.persistence.surreal_client import SurrealClient


async def audit():
    client = SurrealClient()
    await client.connect()

    if hasattr(client._client, "query"):
        # Get count and node types
        node_counts = await client._client.query("SELECT count(), node_type FROM universe_nodes GROUP BY node_type")
        print("📊 PERSISTENCE REPORT (SurrealDB)")
        print("====================================")
        for r in node_counts:
            # Result format varies by result[0]['result'] or directly
            if "result" in r:
                for item in r["result"]:
                    print(f"- {item['node_type']}: {item['count']} records")
            else:
                print(f"- {r.get('node_type', 'unknown')}: {r.get('count', 0)} records")

        # Get the latest discovery summary
        disc = await client._client.query(
            "SELECT content FROM universe_nodes WHERE node_type = 'lab_discovery' ORDER BY created_at DESC LIMIT 1"
        )
        if disc and disc[0].get("result"):
            print("\n✅ LATEST PERSISTENT FINDING:")
            print(f"{disc[0]['result'][0]['content'][:200]}...")


if __name__ == "__main__":
    asyncio.run(audit())
