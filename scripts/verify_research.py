import asyncio
import logging

from cohezion.core.persistence.surreal_client import SurrealClient


# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerifyResearch")


async def main():
    db = SurrealClient()
    try:
        await db.connect()
        print(f"DEBUG: Client Type: {type(db._client)}")
        try:
            import surrealdb

            print(f"DEBUG: surrealdb package: {surrealdb.__file__}")
        except ImportError:
            print("DEBUG: surrealdb import failed")

        # DEBUG INFO
        # info = await db.query("INFO FOR DB")
        # print(f"DB INFO: {info}")

        # WRITE CHECK
        test_id = "test_verify"
        from cohezion.core.persistence.surreal_client import UniverseNode

        await db.store_node(UniverseNode(id=test_id, content="Verification Probe", node_type="probe"))
        print("Stored Probe.")

        # READ CHECK
        query = "SELECT * FROM universe_nodes"
        results = await db.query(query)
        # results is typically [{'result': [...], 'status': 'OK'}]
        # print(f"DEBUG RESULTS RAW: {results}")

        if results and isinstance(results, list):
            res_data = results[0]
            nodes = res_data.get("result", [])
        else:
            nodes = []

        print(f"Found {len(nodes)} research nodes.")
        for n in nodes:
            print(f"- {n.get('id')}: {n.get('content')}")
            # Check 12D physics
            p = n.get("physics_state", {})
            print(f"  Physics: Logic={p.get('dim_7_logic')}, Novelty={p.get('dim_11_novelty')}")

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
