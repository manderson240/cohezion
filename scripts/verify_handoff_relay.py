import asyncio
import logging

from cohezion.agents.controller_agent import ControllerAgent


async def verify_relay():
    logging.basicConfig(level=logging.INFO)
    controller = ControllerAgent()

    print("\n🚀 Starting High-Urgency Research Relay...")
    result = await controller.ignite(
        {
            "query": "Investigate reality precipitation threshold in 12D scalar manifolds.",
            "context": {"priority": "max"},
            "urgency": "high",
        }
    )

    print("\n✅ Synthesis complete.")
    print(f"Confidence: {result['confidence']}")

    if "last_snapshot" in result["context"]:
        print("\n📦 Handoff Snapshot Detected!")
        print("-" * 20)
        print(result["context"]["last_snapshot"][:500] + "...")
        print("-" * 20)
    else:
        print("\n❌ Handoff Snapshot MISSING.")

    # Check SurrealDB directly for the snapshot node
    from cohezion.core.persistence.surreal_client import SurrealClient

    db = SurrealClient()
    await db.connect()
    snapshots = await db.query(
        "SELECT * FROM universe_nodes WHERE node_type = 'session_snapshot' ORDER BY metadata.created_at DESC LIMIT 1"
    )
    records = []
    if snapshots and isinstance(snapshots, list) and len(snapshots) > 0:
        records = snapshots[0].get("result", [])

    await db.close()

    if records:
        print(f"\n✅ Verified SNAPSHOT persistence in SurrealDB: {records[0]['id']}")
    else:
        print("\n❌ SNAPSHOT NOT found in SurrealDB.")


if __name__ == "__main__":
    asyncio.run(verify_relay())
