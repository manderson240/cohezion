import asyncio
from datetime import datetime

from cohezion.core.persistence.surreal_client import SurrealClient


async def repair():
    c = SurrealClient()
    await c.connect()

    print("Repairing created_at field schema violations via Python...")
    # Fetch all nodes that need fixing
    nodes = await c.query("SELECT id, created_at FROM universe_nodes")

    for node in nodes:
        node_id = node["id"]
        ca = node.get("created_at")
        if isinstance(ca, str):
            try:
                # Convert to proper datetime object
                dt = datetime.fromisoformat(ca.replace("Z", "+00:00"))
                # Update specifically this record ID
                await c.query("UPDATE $id SET created_at = $dt", {"id": node_id, "dt": dt})
                print(f"Fixed {node_id}")
            except Exception as e:
                print(f"Failed to fix {node_id}: {e}")

    print("Repair complete.")
    await c.close()


if __name__ == "__main__":
    asyncio.run(repair())
